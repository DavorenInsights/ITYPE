# ============================================================
# I-TYPE ENGINE (FINAL FIXED VERSION)
# ============================================================

import math
import random


# ============================================================
# 1. NORMALISE SCORES (SUM-BASED, NOT AVERAGE-BASED)
# ============================================================

def normalize_scores(raw_answers):
    """
    Converts raw 1–5 values (with reverse scoring) into
    dimension totals and then scales each dimension to 0–100.
    This preserves variance and prevents archetype collapse.
    """

    dims = ["thinking", "execution", "risk", "motivation", "team", "commercial"]

    scores = {d: 0 for d in dims}
    counts = {d: 0 for d in dims}

    # SUM raw scores per dimension (after reverse coding)
    for entry in raw_answers.values():
        dim = entry["dimension"]
        val = entry["value"]

        if entry.get("reverse", False):
            val = 6 - val  # reverse Likert

        scores[dim] += val
        counts[dim] += 1

    # Convert to percent-of-maximum
    final_scores = {}
    for d in dims:
        max_score = counts[d] * 5
        if max_score == 0:
            final_scores[d] = 50  # neutral fallback
        else:
            final_scores[d] = (scores[d] / max_score) * 100

    return final_scores


# ============================================================
# 2. ARCHETYPE MATCHING — TRUE EUCLIDEAN DISTANCE
# ============================================================

def determine_archetype(scores, archetypes):
    """
    Selects the archetype whose signature vector is closest
    to the user's score vector using Euclidean distance.
    """

    best_name = None
    best_dist = float("inf")
    best_data = None

    for name, data in archetypes.items():

        sig = data.get("signature", {})
        dims = set(scores.keys()) & set(sig.keys())

        if not dims:
            continue

        dist = math.sqrt(sum(
            (scores[d] - sig[d]) ** 2 for d in dims
        ))

        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_data = data

    return best_name, best_data


# ============================================================
# 3. MONTE CARLO STABILITY TEST
# ============================================================

def monte_carlo_probabilities(base_scores, archetypes, runs=5000, noise=0.10):
    """
    Runs perturbations of user scores to estimate:
      - Identity stability
      - Full identity distribution
      - Shadow archetype
    """

    counts = {name: 0 for name in archetypes}

    for _ in range(runs):

        perturbed = {}
        for dim, val in base_scores.items():
            delta = random.gauss(0, noise * 100)   # ±10% variation
            perturbed[dim] = max(0, min(100, val + delta))

        name, _ = determine_archetype(perturbed, archetypes)
        counts[name] += 1

    total = sum(counts.values())
    probs = {a: (c / total) * 100 for a, c in counts.items()}

    # Determine primary
    primary = max(probs, key=probs.get)
    stability = probs[primary]

    # Shadow
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    shadow = sorted_probs[1] if len(sorted_probs) > 1 else ("None", 0)

    return probs, stability, shadow


# ============================================================
# 4. OPTIONAL — DISTANCE MATRIX (FOR HEATMAP DEBUGGING)
# ============================================================

def compute_archetype_distances(scores, archetypes):
    """
    Returns raw Euclidean distances — used for diagnostics.
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
