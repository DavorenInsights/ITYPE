import math
import random

# ============================================================
# NORMALISE RAW QUESTION SCORES (1–5 → 0–100)
# ============================================================

def normalize_scores(raw_answers):
    dims = {
        "thinking": [],
        "execution": [],
        "risk": [],
        "motivation": [],
        "team": [],
        "commercial": []
    }

    for q, info in raw_answers.items():
        val = info["value"]

        # Reverse-coded questions
        if info.get("reverse", False):
            val = 6 - val

        dims[info["dimension"]].append(val)

    final_scores = {}
    for d, values in dims.items():
        if not values:
            final_scores[d] = 0
        else:
            avg = sum(values) / len(values)
            final_scores[d] = ((avg - 1) / 4) * 100

    return final_scores


# ============================================================
# SCENARIO NORMALISATION + COMBINATION LOGIC
# ============================================================

def detect_max_scenario_value(scenario_scores_raw):
    """
    Automatically detect the maximum theoretical scenario mapping value.
    Prevents needing to hardcode MAX_SCENARIO = 3.
    """
    max_val = max(abs(v) for v in scenario_scores_raw.values())
    return max(max_val, 1)  # avoid divide-by-zero


def normalize_scenario_scores(scenario_scores_raw):
    """
    Normalize scenario outputs to the same 0–100 scale as questionnaire.
    Auto-detects the scenario mapping scale.
    """
    max_score = detect_max_scenario_value(scenario_scores_raw)
    normalized = {}

    for k, val in scenario_scores_raw.items():
        normalized[k] = (val / max_score) * 100

    return normalized


def combine_with_scenarios(question_scores, scenario_scores_raw):
    """
    Combine the questionnaire scores with scenario scores.
    Uses auto-normalized scenario scores.
    """
    weights = {
        "questions": 0.70,
        "scenarios": 0.30
    }

    scenario_norm = normalize_scenario_scores(scenario_scores_raw)

    combined = {}
    for dim in question_scores.keys():
        combined[dim] = (
            question_scores[dim] * weights["questions"] +
            scenario_norm[dim] * weights["scenarios"]
        )

    return combined


# ============================================================
# ARCHETYPE MATCHING (EUCLIDEAN DISTANCE)
# ============================================================

def determine_archetype(scores, archetypes):
    best_name = None
    best_dist = float("inf")
    best_data = None

    for name, data in archetypes.items():
        signature = data.get("signature", {})

        # dimensions common to both signature & scores
        dims = set(scores.keys()) & set(signature.keys())

        if not dims:
            continue

        dist = math.sqrt(sum(
            (scores[d] - signature[d]) ** 2
            for d in dims
        ))

        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_data = data

    return best_name, best_data


# ============================================================
# MONTE CARLO SIMULATION (FAIR + BALANCED)
# ============================================================

def monte_carlo_probabilities(base_scores, archetypes, runs=5000, noise=0.07):
    """
    noise=0.07 → ±7% std deviation of absolute scale (100)
    Ensures fairness without overwhelming signal.
    """
    counts = {name: 0 for name in archetypes.keys()}

    for _ in range(runs):
        perturbed = {}

        for dim, val in base_scores.items():
            delta = random.gauss(0, noise * 100)
            perturbed_val = max(0, min(100, val + delta))
            perturbed[dim] = perturbed_val

        name, _ = determine_archetype(perturbed, archetypes)
        counts[name] += 1

    total = sum(counts.values())
    probs = {a: (c / total) * 100 for a, c in counts.items()}

    # Primary archetype
    primary = max(probs, key=probs.get)
    stability = probs[primary]

    # Shadow archetype (2nd place)
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    shadow = sorted_probs[1] if len(sorted_probs) > 1 else ("None", 0)

    return probs, stability, shadow


# ============================================================
# OPTIONAL — DIAGNOSTIC: DISTANCE HEATMAP PREP (ADVANCED)
# ============================================================

def compute_archetype_distances(scores, archetypes):
    """
    Returns a dictionary of raw Euclidean distances
    before conversion to probabilities.
    Useful for debugging model geometry.
    """
    distances = {}
    for name, data in archetypes.items():
        sig = data["signature"]
        dims = set(scores.keys()) & set(sig.keys())

        dist = math.sqrt(sum(
            (scores[d] - sig[d]) ** 2 for d in dims
        ))

        distances[name] = dist

    return distances
