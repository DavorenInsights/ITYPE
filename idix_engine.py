import math
import random
from typing import Dict, Tuple, Any


# ============================================================
# CORE DIMENSIONS + WEIGHTS (MODEL B — WEIGHTED EUCLIDEAN)
# ============================================================

DIMENSIONS = ["thinking", "execution", "risk", "motivation", "team", "commercial"]

# Heavier weight on thinking + execution, medium on risk + motivation,
# slightly lower on team + commercial: reflects innovation reality
DIM_WEIGHTS = {
    "thinking": 1.2,
    "execution": 1.2,
    "risk": 1.0,
    "motivation": 1.0,
    "team": 0.8,
    "commercial": 0.8,
}


# ============================================================
# 1) NORMALISE RAW QUESTION SCORES (1–5 → 0–100)
# ============================================================

def normalize_scores(raw_answers: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """
    Convert raw question answers (1–5 Likert) into 0–100 scores
    for each innovation dimension.

    raw_answers structure:
    {
        "question text": {
            "value": int 1–5,
            "dimension": "thinking" | "execution" | ...,
            "reverse": bool
        },
        ...
    }

    Scaling:
        1 → 0
        3 → 50
        5 → 100
    """
    dims = {d: [] for d in DIMENSIONS}

    for _, info in raw_answers.items():
        dim = info.get("dimension")
        if dim not in dims:
            # ignore unknown dimensions defensively
            continue

        val = info.get("value", 3)

        # Reverse-coded questions: 1 ↔ 5, 2 ↔ 4, 3 ↔ 3
        if info.get("reverse", False):
            val = 6 - val

        # clamp just in case
        val = max(1, min(5, val))
        dims[dim].append(val)

    final_scores: Dict[str, float] = {}

    for d, values in dims.items():
        if not values:
            final_scores[d] = 0.0
        else:
            avg = sum(values) / len(values)  # average 1–5
            # map 1–5 to 0–100 linearly
            final_scores[d] = ((avg - 1.0) / 4.0) * 100.0

    return final_scores


# ============================================================
# 2) WEIGHTED EUCLIDEAN DISTANCE
# ============================================================

def _weighted_distance(
    scores: Dict[str, float],
    signature: Dict[str, float],
    weights: Dict[str, float] = DIM_WEIGHTS,
) -> float:
    """
    Compute weighted Euclidean distance between user scores and an archetype signature.

    d = sqrt( Σ w_d * (score_d - sig_d)^2 )
    Only uses dimensions present in both user scores and signature.
    """
    total = 0.0
    used_dims = 0

    for dim, w in weights.items():
        if dim not in scores or dim not in signature:
            continue
        diff = scores[dim] - signature[dim]
        total += w * (diff ** 2)
        used_dims += 1

    if used_dims == 0:
        # no overlapping dimensions → treat as infinitely far
        return float("inf")

    return math.sqrt(total)


# ============================================================
# 3) ARCHETYPE MATCHING
# ============================================================

def determine_archetype(
    scores: Dict[str, float],
    archetypes: Dict[str, Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    """
    Determine the best-fit archetype given final dimension scores (0–100)
    using weighted Euclidean distance.

    Returns:
        (best_name, archetype_data)

    If no archetype can be matched, returns (None, None).
    """
    best_name = None
    best_dist = float("inf")
    best_data: Dict[str, Any] = None

    for name, data in archetypes.items():
        signature = data.get("signature", {})
        if not isinstance(signature, dict) or not signature:
            continue

        dist = _weighted_distance(scores, signature)

        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_data = data

    return best_name, best_data


# ============================================================
# 4) MONTE CARLO PROBABILITIES (IDENTITY SPECTRUM)
# ============================================================

def monte_carlo_probabilities(
    base_scores: Dict[str, float],
    archetypes: Dict[str, Dict[str, Any]],
    runs: int = 5000,
    noise: float = 0.07,
) -> Tuple[Dict[str, float], float, Tuple[str, float]]:
    """
    Run Monte Carlo simulations to estimate how stable the archetype is.

    For each run:
        - Add Gaussian noise (mean 0, std = noise * 100) to each dimension.
        - Clamp scores to [0, 100].
        - Recompute the best-fit archetype via weighted Euclidean distance.

    Returns:
        probs: dict of archetype → probability (%) across all runs.
        stability: primary archetype probability (%).
        shadow: (2nd_best_name, 2nd_best_probability).
    """
    if not archetypes:
        return {}, 0.0, ("None", 0.0)

    counts = {name: 0 for name in archetypes.keys()}

    for _ in range(runs):
        perturbed = {}

        for dim in DIMENSIONS:
            val = base_scores.get(dim, 0.0)
            delta = random.gauss(0.0, noise * 100.0)
            perturbed_val = max(0.0, min(100.0, val + delta))
            perturbed[dim] = perturbed_val

        name, _ = determine_archetype(perturbed, archetypes)
        if name is not None:
            counts[name] += 1

    total = sum(counts.values()) or 1  # avoid divide-by-zero
    probs = {a: (c / total) * 100.0 for a, c in counts.items()}

    # Primary archetype
    primary = max(probs, key=probs.get)
    stability = probs[primary]

    # Shadow archetype (2nd place)
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_probs) > 1:
        shadow = sorted_probs[1]
    else:
        shadow = ("None", 0.0)

    return probs, stability, shadow


# ============================================================
# 5) OPTIONAL DIAGNOSTIC: RAW DISTANCES
# ============================================================

def compute_archetype_distances(
    scores: Dict[str, float],
    archetypes: Dict[str, Dict[str, Any]],
) -> Dict[str, float]:
    """
    Returns a dictionary of weighted Euclidean distances from the user scores
    to each archetype signature. Smaller = closer.

    Useful for debugging geometry or building advanced visualisations.
    """
    distances: Dict[str, float] = {}

    for name, data in archetypes.items():
        sig = data.get("signature", {})
        if not isinstance(sig, dict) or not sig:
            continue

        distances[name] = _weighted_distance(scores, sig)

    return distances
