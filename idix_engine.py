# ===============================================================
# I-TYPE ENGINE — OPTIMISED ARCHETYPES + CLEAN EUCLIDEAN MODEL
# ===============================================================

import math
import random


# ---------------------------------------------------------------
# NORMALISE RAW QUESTION SCORES (1–5 → 0–100)
# ---------------------------------------------------------------

def normalize_scores(raw_answers):
    """
    Takes raw answer dict:
    {
        "question text": {"value": 1–5, "dimension": "...", "reverse": bool},
        ...
    }

    Produces dimension scores 0–100.
    """

    dims = {
        "thinking": [],
        "execution": [],
        "risk": [],
        "motivation": [],
        "team": [],
        "commercial": [],
    }

    for _, info in raw_answers.items():
        val = info["value"]

        # Reverse coded → invert 1–5 scale
        if info.get("reverse", False):
            val = 6 - val

        dims[info["dimension"]].append(val)

    final_scores = {}
    for dim, values in dims.items():
        if not values:
            final_scores[dim] = 0
        else:
            avg = sum(values) / len(values)
            # Convert from 1–5 to 0–100
            final_scores[dim] = ((avg - 1) / 4) * 100

    return final_scores


# ---------------------------------------------------------------
# Z-SCORE DISTANCING FOR BETTER PSYCHOMETRIC SEPARATION
# ---------------------------------------------------------------

def z_distance(user_scores, archetype_sig):
    """
    Computes Euclidean distance in Z-space.
    This prevents dimensions with larger numerical variance from dominating.
    """

    dims = ["thinking", "execution", "risk", "motivation", "team", "commercial"]

    # Standard deviations chosen to balance scale influence
    # (Prevents Thinking/Execution from overpowering Commercial/Team)
    stdev = {
        "thinking": 18,
        "execution": 18,
        "risk": 18,
        "motivation": 18,
        "team": 18,
        "commercial": 18,
    }

    acc = 0
    for d in dims:
        diff = (user_scores[d] - archetype_sig[d]) / stdev[d]
        acc += diff * diff

    return math.sqrt(acc)


# ---------------------------------------------------------------
# DETERMINE CLOSEST ARCHETYPE USING Z-DIST EUCLIDEAN
# ---------------------------------------------------------------

def determine_archetype(scores, archetypes):
    best_name = None
    best_dist = float("inf")
    best_data = None

    for name, data in archetypes.items():
        sig = data.get("signature", {})
        if not sig:
            continue

        dist = z_distance(scores, sig)

        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_data = data

    return best_name, best_data


# ---------------------------------------------------------------
# MONTE-CARLO — IDENTITY STABILITY + SHADOW ARCHETYPE
# ---------------------------------------------------------------

def monte_carlo_probabilities(base_scores, archetypes, runs=5000, noise=0.06):
    """
    Adds Gaussian noise (±6%) to user scores and reclassifies.
    Determines:
      • Identity stability
      • Probability distribution
      • Shadow archetype
    """

    names = list(archetypes.keys())
    counts = {name: 0 for name in names}

    for _ in range(runs):

        perturbed = {}

        for dim, val in base_scores.items():
            delta = random.gauss(0, noise * 100)
            perturbed[dim] = max(0, min(100, val + delta))

        name, _ = determine_archetype(perturbed, archetypes)
        counts[name] += 1

    total = sum(counts.values())
    probs = {name: (counts[name] / total) * 100 for name in names}

    # Primary
    primary = max(probs, key=probs.get)
    stability = probs[primary]

    # Shadow = second most likely
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    shadow = sorted_probs[1] if len(sorted_probs) > 1 else ("None", 0)

    return probs, stability, shadow


# ---------------------------------------------------------------
# OPTIONAL — RAW DISTANCE DIAGNOSTICS FOR DEBUGGING
# ---------------------------------------------------------------

def compute_archetype_distances(scores, archetypes):
    """
    Returns raw z-distances to all archetypes.
    Debugging: lets you see how close each one was.
    """

    out = {}
    for name, data in archetypes.items():
        sig = data["signature"]
        out[name] = z_distance(scores, sig)

    return out
