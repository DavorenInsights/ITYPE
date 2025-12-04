import streamlit as st
import json
import plotly.graph_objects as go

from idix_engine import (
    normalize_scores,
    determine_archetype,
    monte_carlo_probabilities,
    compute_archetype_distances,
)

# Optional: anonymous logging (safe if file missing)
try:
    from data_logger import log_response
    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False


# ============================================================
# SESSION STATE INITIALISATION
# ============================================================

if "step" not in st.session_state:
    st.session_state["step"] = 1  # 1 = Questions, 2 = Results

if "has_results" not in st.session_state:
    st.session_state["has_results"] = False

if "open_archetype" not in st.session_state:
    st.session_state["open_archetype"] = None

# persistent answer store (fixed)
if "answers" not in st.session_state:
    st.session_state["answers"] = {}


# ============================================================
# LOAD CSS
# ============================================================

def load_css():
    try:
        with open("assets/styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("⚠ Missing CSS file: assets/styles.css")


load_css()


# ============================================================
# LOAD JSON HELPERS
# ============================================================

def load_json(path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading {path}: {e}")
        return default


questions = load_json("data/questions.json", default=[])
archetypes = load_json("data/archetypes.json", default={})


# ============================================================
# HERO SECTION
# ============================================================

st.markdown("""
<div class="hero-wrapper">
<div class="hero">
<div class="hero-glow"></div>
<div class="hero-particles"></div>
<div class="hero-content">
<h1 class="hero-title">I-TYPE — Innovator Type Assessment</h1>
<p class="hero-sub">Powered by the Innovator DNA Index™</p>
</div>
</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# STEP PROGRESS BAR (2 STEPS)
# ============================================================

step = st.session_state["step"]
total_steps = 2

step_labels = {
    1: "Step 1 of 2 — Innovation Profile Questionnaire",
    2: "Step 2 of 2 — Your Innovator Type & Results",
}

st.markdown(f"### {step_labels[step]}")
st.progress(step / total_steps)


# ============================================================
# HELPERS TO RECONSTRUCT ANSWERS FROM STATE (FIXED)
# ============================================================

def get_answers_from_state(questions_list):
    """
    Builds the answers dict from st.session_state["answers"]
    and the questions configuration.
    """
    answers = {}
    for i, q in enumerate(questions_list):
        key = f"q{i}"
        val = st.session_state["answers"].get(key)

        if val is None:
            # As a fallback, default to 3 (neutral)
            val = 3

        answers[q["question"]] = {
            "value": val,
            "dimension": q.get("dimension", "thinking"),
            "reverse": q.get("reverse", False),
        }

    return answers


# ============================================================
# LIKERT LEGEND (1–5 MEANING)
# ============================================================

LIKERT_LEGEND = """
<div class="likert-legend">
<span>1 = Strongly Disagree</span>
<span>2 = Disagree</span>
<span>3 = Neutral</span>
<span>4 = Agree</span>
<span>5 = Strongly Agree</span>
</div>
"""


# ============================================================
# STEP 1 — QUESTIONNAIRE
# ============================================================

if step == 1:

    if not questions:
        st.error("❌ No questions found. Check data/questions.json.")
    else:
        st.markdown(LIKERT_LEGEND, unsafe_allow_html=True)

        for i, q in enumerate(questions):
            text = q.get("question", f"Question {i+1}")

            # Question block
            st.markdown(f"""
            <div class="itype-question">
              <p><b>{text}</b></p>
            </div>
            """, unsafe_allow_html=True)

            # Slider directly below question (FIXED: use persistent answers store)
            value = st.slider(
                label="",
                min_value=1,
                max_value=5,
                value=st.session_state["answers"].get(f"q{i}", 3),
                key=f"q{i}",
                help="1 = Strongly Disagree · 5 = Strongly Agree"
            )

            # Persist in answers dict
            st.session_state["answers"][f"q{i}"] = value

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # Reset all answers + state
    with col1:
        if st.button("Reset"):
            # Clear all question values
            for key in list(st.session_state.keys()):
                if key.startswith("q"):
                    del st.session_state[key]

            st.session_state["answers"] = {}
            st.session_state["step"] = 1
            st.session_state["has_results"] = False
            st.session_state["open_archetype"] = None
            st.rerun()

    # Move to Step 2 and freeze answers
    with col2:
        if st.button("Next ➜ See My Results"):
            # Persist all current sliders into answers store
            for i in range(len(questions)):
                st.session_state["answers"][f"q{i}"] = st.session_state.get(f"q{i}", 3)

            st.session_state["step"] = 2
            st.rerun()


# ============================================================
# STEP 2 — RESULTS
# ============================================================

elif step == 2:

    if not questions or not archetypes:
        st.error("❌ Missing questions or archetypes configuration.")
    else:
        answers = get_answers_from_state(questions)

        # ----------------------------------------------
        # CONSENT
        # ----------------------------------------------
        st.markdown("""
        <div style="margin-top:10px; margin-bottom:8px; padding:10px;
             border:1px solid #00eaff55; border-radius:8px; font-size:0.9rem;">
        <b>Optional:</b> Allow anonymous numeric scores to help improve I-TYPE.
        </div>
        """, unsafe_allow_html=True)

        consent = st.checkbox(
            "I agree to anonymous score logging (no personal data).",
            value=True
        )

        if consent:
            st.info("✅ Thank you — anonymous numeric values only.")

        # ----------------------------------------------
        # CALCULATE BUTTON
        # ----------------------------------------------
        calc = st.button("🚀 Calculate My Innovator Type")

        if calc:
            st.session_state["has_results"] = True
            st.session_state["open_archetype"] = None

            # STEP 1: NORMALISE SCORES
            final_scores = normalize_scores(answers)

            # DEBUG OUTPUT
            st.write("DEBUG — Final Scores (0–100):", final_scores)

            # STEP 2: MATCH ARCHETYPE
            primary_name, archetype_data = determine_archetype(final_scores, archetypes)

                # STEP 3: MONTE CARLO
                probs, stability, shadow = monte_carlo_probabilities(
                    final_scores,
                    archetypes
                )

                shadow_name, shadow_pct = shadow

                # LOGGING
                if HAS_LOGGER and consent:
                    try:
                        log_response(
                            final_archetype=primary_name,
                            stability=stability,
                            shadow=shadow,
                            scores=final_scores,
                            raw_answers=answers
                        )
                    except Exception as e:
                        st.warning(f"Logging failed: {e}")

                # ----------------------------------------------
                # HERO CARD + MAIN ARCHETYPE IMAGE
                # ----------------------------------------------
                img_path = f"data/archetype_images/{primary_name}.png"

                try:
                    st.image(img_path, use_column_width=False)
                except Exception:
                    # Image optional, don't break if not present
                    pass

                st.markdown(f"""
                <div class="itype-result-card">
                <h1>{primary_name}</h1>
                <p>{archetype_data.get("description", "")}</p>
                <p><b>Stability:</b> {stability:.1f}%</p>
                <p><b>Shadow archetype:</b> {shadow_name} ({shadow_pct:.1f}%)</p>
                </div>
                """, unsafe_allow_html=True)

                # ----------------------------------------------
                # RADAR CHART — FIXED DIMENSION ORDER
                # ----------------------------------------------
                st.markdown("<div class='itype-chart-box'>", unsafe_allow_html=True)

                dims = ["thinking", "execution", "risk", "motivation", "team", "commercial"]
                vals = [final_scores.get(d, 0.0) for d in dims]

                vals_closed = vals + [vals[0]]
                dims_closed = dims + [dims[0]]

                radar = go.Figure()
                radar.add_trace(go.Scatterpolar(
                    r=vals_closed,
                    theta=dims_closed,
                    fill='toself',
                    fillcolor='rgba(0,234,255,0.25)',
                    line_color='#00eaff',
                    line_width=3,
                    marker=dict(size=6, color="#00eaff")
                ))

                radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100],
                            tickfont=dict(color="#e5f4ff"),
                            gridcolor="rgba(255,255,255,0.08)",
                            linewidth=1
                        ),
                        angularaxis=dict(
                            tickfont=dict(color="#e5f4ff"),
                            gridcolor="rgba(255,255,255,0.08)"
                        )
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    margin=dict(l=40, r=40, t=30, b=30)
                )

                st.plotly_chart(radar, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # ----------------------------------------------
                # IDENTITY SPECTRUM BAR CHART
                # ----------------------------------------------
                st.markdown("<div class='itype-chart-box'>", unsafe_allow_html=True)

                sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)

                bar_fig = go.Figure()
                bar_fig.add_trace(go.Bar(
                    x=[p[0] for p in sorted_probs],
                    y=[p[1] for p in sorted_probs],
                    marker_color="#00eaff"
                ))
                bar_fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_title="Probability (%)",
                    xaxis_title="Archetype",
                    font=dict(color="#e5f4ff")
                )

                st.plotly_chart(bar_fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # ----------------------------------------------
                # HEATMAP (3×3 ARCHETYPE GRID)
                # ----------------------------------------------
                st.markdown("<div class='itype-chart-box'>", unsafe_allow_html=True)

                heat_archetypes = [
                    ["Visionary", "Strategist", "Storyteller"],
                    ["Catalyst", "Apex Innovator", "Integrator"],
                    ["Engineer", "Operator", "Experimenter"]
                ]

                heat_values = [
                    [probs.get(a, 0.0) for a in row]
                    for row in heat_archetypes
                ]

                row_labels = ["Ideation Cluster", "Activation Cluster", "Execution Cluster"]
                col_labels = ["Visionary", "Strategist", "Storyteller"]

                heat_fig = go.Figure(data=go.Heatmap(
                    z=heat_values,
                    x=col_labels,
                    y=row_labels,
                    colorscale="blues",
                    zmin=0,
                    zmax=max([max(row) for row in heat_values] + [1]),
                    showscale=True,
                    hoverinfo="skip"
                ))

                # Add annotations (black text inside cells)
                annotations = []
                for i, row in enumerate(heat_archetypes):
                    for j, archetype in enumerate(row):
                        pct = probs.get(archetype, 0.0)
                        annotations.append(dict(
                            x=col_labels[j],
                            y=row_labels[i],
                            text=f"<b>{archetype}</b><br>{pct:.1f}%",
                            showarrow=False,
                            font=dict(size=13, color="black"),
                            align="center"
                        ))

                heat_fig.update_layout(
                    annotations=annotations,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e5f4ff"),
                    title="Identity Heatmap",
                    margin=dict(l=40, r=40, t=60, b=40),
                    xaxis=dict(side="top")
                )

                st.plotly_chart(heat_fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # Optional extra debug
                debug_energy = compute_archetype_distances(final_scores, archetypes)
                if isinstance(debug_energy, dict) and "energy" in debug_energy:
                    st.write("DEBUG energies:", debug_energy["energy"])

                # ----------------------------------------------
                # DETAILED BREAKDOWN
                # ----------------------------------------------
                st.markdown("<hr><h2>Your Innovator Breakdown</h2>", unsafe_allow_html=True)

                st.markdown("<h3>Strengths</h3>", unsafe_allow_html=True)
                for s in archetype_data.get("strengths", []):
                    st.markdown(
                        f"<div class='itype-strength-card'>• {s}</div>",
                        unsafe_allow_html=True
                    )

                st.markdown("<h3 style='margin-top:20px;'>Growth Edges & Risks</h3>",
                            unsafe_allow_html=True)
                for r in archetype_data.get("risks", []):
                    st.markdown(
                        f"<div class='itype-risk-card'>• {r}</div>",
                        unsafe_allow_html=True
                    )

                st.markdown("<h3 style='margin-top:20px;'>Recommended Innovation Pathways</h3>",
                            unsafe_allow_html=True)
                for pth in archetype_data.get("pathways", []):
                    st.markdown(
                        f"<div class='itype-pathway-card'>• {pth}</div>",
                        unsafe_allow_html=True
                    )

                st.markdown("<h3 style='margin-top:20px;'>Suggested Business Models</h3>",
                            unsafe_allow_html=True)
                for bm in archetype_data.get("business_models", []):
                    st.markdown(
                        f"<div class='itype-business-card'>• {bm}</div>",
                        unsafe_allow_html=True
                    )

                st.markdown("<h3 style='margin-top:20px;'>Funding Strategy Fit</h3>",
                            unsafe_allow_html=True)
                for fs in archetype_data.get("funding_strategy", []):
                    st.markdown(
                        f"<div class='itype-funding-card'>• {fs}</div>",
                        unsafe_allow_html=True
                    )

                st.markdown("<hr><h3>How to Interpret Your Results</h3>", unsafe_allow_html=True)
                st.markdown("""
                - **Stability %** — how consistent your identity is across many simulations.  
                - **Shadow archetype** — your second-strongest identity.  
                - **Identity spectrum** — how your profile spreads across all archetypes.  
                - **Heatmap** — how you cluster in the 3×3 innovation matrix.  
                - **Radar chart** — your core innovation dimensions:
                  thinking, execution, risk, motivation, team, commercial.
                """)

                st.markdown("""
                <p style="font-size: 0.85rem; opacity: 0.8; margin-top: 1.5rem;">
                  🔒 <b>Privacy:</b> Only numeric scores are stored (if you opt in).
                  No names, emails, or identifying details are collected.
                </p>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("⬅ Back to Questions"):
            st.session_state["step"] = 1
            st.session_state["has_results"] = False
            st.session_state["open_archetype"] = None
            st.rerun()

    with col2:
        if st.button("🔄 Start Over"):
            for key in list(st.session_state.keys()):
                if key.startswith("q"):
                    del st.session_state[key]
            st.session_state["answers"] = {}
            st.session_state["step"] = 1
            st.session_state["has_results"] = False
            st.session_state["open_archetype"] = None
            st.rerun()


# ============================================================
# ARCHETYPE GRID WITH SIMPLE BUTTONS (3×3)
# ============================================================

if st.session_state.get("has_results") and archetypes:
    if "open_archetype" not in st.session_state:
        st.session_state["open_archetype"] = None

    st.markdown("<hr class='hr-neon'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;'>Explore All Archetypes</h2>",
                unsafe_allow_html=True)
    st.markdown("<p style='opacity:0.85; text-align:center;'>Click a tile to reveal its profile.</p>",
                unsafe_allow_html=True)

    cols = st.columns(3)

    for idx, (name, data) in enumerate(archetypes.items()):
        with cols[idx % 3]:
            if st.button(name, key=f"arch_btn_{name}", use_container_width=True):
                if st.session_state["open_archetype"] == name:
                    st.session_state["open_archetype"] = None
                else:
                    st.session_state["open_archetype"] = name

    selected = st.session_state["open_archetype"]

    if selected is not None and selected in archetypes:
        img_path = f"data/archetype_images/{selected}.png"

        try:
            st.image(img_path, use_column_width=True)
        except Exception:
            pass

        info = archetypes[selected]

        st.markdown(f"""
        <div class="archetype-panel">
        <h2 style="text-align:center;">{selected}</h2>
        <p>{info.get("description","")}</p>

        <h4>Strengths</h4>
        <ul>{''.join(f'<li>{s}</li>' for s in info.get('strengths', []))}</ul>

        <h4>Risks</h4>
        <ul>{''.join(f'<li>{r}</li>' for r in info.get('risks', []))}</ul>

        <h4>Pathways</h4>
        <ul>{''.join(f'<li>{p}</li>' for p in info.get('pathways', []))}</ul>

        <h4>Business Models</h4>
        <ul>{''.join(f'<li>{bm}</li>' for bm in info.get('business_models', []))}</ul>

        <h4>Funding Strategy Fit</h4>
        <ul>{''.join(f'<li>{fs}</li>' for fs in info.get('funding_strategy', []))}</ul>
        </div>
        """, unsafe_allow_html=True)

