import math
import random

# ============================================================
# NORMALISE QUESTIONNAIRE SCORES (1–5 → 0–100)
# ============================================================

def normalize_scores(answers_dict):
    """
    Converts raw slider values into 0–100 scale per dimension.
    Structure:
    {
        "question": {"value": 1–5, "dimension": "thinking", "reverse": True/False}
    }
    """

    dim_totals = {
        "thinking": 0,
        "execution": 0,
        "risk": 0,
        "motivation": 0,
        "team": 0,
        "commercial": 0,
    }
    dim_counts = {k: 0 for k in dim_totals}

    # Combine values per dimension
    for q, meta in answers_dict.items():
        value = meta["value"]
        dim = meta["dimension"]
        rev = meta.get("reverse", False)

        if rev:
            value = 6 - value  # reverse-coded sliders

        dim_totals[dim] += value
        dim_counts[dim] += 1

    # Convert to percentage
    out = {}
    for dim in dim_totals:
        if dim_counts[dim] == 0:
            out[dim] = 50  # neutral fallback
        else:
            avg = dim_totals[dim] / dim_counts[dim]  # in 1–5 range
            out[dim] = (avg - 1) / 4 * 100  # → 0–100 scale

    return out


# ============================================================
# Z-SCORE NORMALISATION ACROSS ARCHETYPES
# ============================================================

def compute_z_scores(user_scores, archetypes):
    """
    Standardises each dimension using archetype means & std.
    Prevents dimensions with larger variance from dominating.
    """

    dims = list(user_scores.keys())

    # Collect archetype dimension values
    dim_vals = {d: [] for d in dims}
    for name, data in archetypes.items():
        sig = data["signature"]
        for d in dims:
            dim_vals[d].append(sig[d])

    # Compute µ and σ for each dimension
    dim_mean = {}
    dim_std = {}

    for d in dims:
        arr = dim_vals[d]
        mean = sum(arr) / len(arr)
        var = sum((v - mean) ** 2 for v in arr) / len(arr)
        std = max(math.sqrt(var), 1e-6)  # avoid zero division
        dim_mean[d] = mean
        dim_std[d] = std

    # Convert user to z-scores
    user_z = {d: (user_scores[d] - dim_mean[d]) / dim_std[d] for d in dims}

    # Convert archetypes to z-scores
    arch_z = {}
    for name, data in archetypes.items():
        sig = data["signature"]
        arch_z[name] = {
            d: (sig[d] - dim_mean[d]) / dim_std[d]
            for d in dims
        }

    return user_z, arch_z


# ============================================================
# DETERMINE PRIMARY ARCHETYPE (Z-SPACE EUCLIDEAN)
# ============================================================

def determine_archetype(final_scores, archetypes):
    """
    Returns (best_name, archetype_data)
    """

    user_z, arch_z = compute_z_scores(final_scores, archetypes)

    best_name = None
    best_dist = float("inf")
    best_data = None

    for name, zd in arch_z.items():
        dist = math.sqrt(sum((user_z[d] - zd[d]) ** 2 for d in user_z))

        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_data = archetypes[name]

    return best_name, best_data


# ============================================================
# MONTE CARLO — IDENTITY STABILITY & SHADOW ARCHETYPE
# ============================================================

def monte_carlo_probabilities(base_scores, archetypes, runs=5000, noise=0.07):
    """
    noise=0.07 → ±7% standard deviation (on 0–100 scale)
    """

    counts = {name: 0 for name in archetypes}

    for _ in range(runs):
        # Perturb each dimension
        perturbed = {
            d: max(0, min(100, base_scores[d] + random.gauss(0, noise * 100)))
            for d in base_scores
        }

        name, _ = determine_archetype(perturbed, archetypes)
        counts[name] += 1

    total = sum(counts.values())
    probs = {a: (counts[a] / total) * 100 for a in counts}

    # Primary
    primary = max(probs, key=probs.get)
    stability = probs[primary]

    # Shadow
    ordered = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    shadow = ordered[1] if len(ordered) > 1 else ("None", 0)

    return probs, stability, shadow
