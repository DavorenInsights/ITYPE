# ============================================================
# I-TYPE ENGINE — ENERGY LANDSCAPE VERSION
# ============================================================
# This module replaces simple Euclidean matching with a
# physics-inspired "energy landscape" model:
#
# - Each archetype is a potential well in 6D space.
# - Your scores sit on that landscape.
# - The archetype with the LOWEST ENERGY is your type.
#
# Public API (unchanged):
#   - normalize_scores(raw_answers) -> dict
#   - determine_archetype(scores, archetypes) -> (name, data)
#   - monte_carlo_probabilities(scores, archetypes, ...) -> (probs, stability, shadow)
#   - compute_archetype_distances(scores, archetypes) -> dict (diagnostic)
#
# You do NOT need to change any imports in I-Type.py.
# ============================================================

import math
import random

# ------------------------------------------------------------
# 1. NORMALISE SCORES (SUM-BASED → 0–100 PER DIMENSION)
# ------------------------------------------------------------

def normalize_scores(raw_answers):
    """
    Converts raw 1–5 Likert values (with reverse coding) into
    0–100 scores per dimension.

    - We sum answers per dimension (not just average).
    - Then scale by maximum possible per dimension.
    - This preserves variance and keeps all 6 axes comparable.
    """

    dims = ["thinking", "execution", "risk", "motivation", "team", "commercial"]

    scores = {d: 0.0 for d in dims}
    counts = {d: 0 for d in dims}

    for entry in raw_answers.values():
        dim = entry["dimension"]
        val = entry["value"]

        # Reverse-coded items: 1↔5, 2↔4, 3 stays 3
        if entry.get("reverse", False):
            val = 6 - val

        scores[dim] += float(val)
        counts[dim] += 1

    final_scores = {}
    for d in dims:
        max_score = counts[d] * 5.0
        if max_score <= 0:
            # If a dimension had no questions (should not happen),
            # fall back to neutral 50.
            final_scores[d] = 50.0
        else:
            final_scores[d] = (scores[d] / max_score) * 100.0

    return final_scores


# ------------------------------------------------------------
# 2. ENERGY LANDSCAPE ENGINE
# ------------------------------------------------------------

def _compute_archetype_energy(
    scores,
    signature,
    dim_weights=None,
    lambda_curvature=0.6,
    rarity_weight=0.25,
):
    """
    Core physics-inspired energy model.

    Each archetype is treated as a "potential well" in 6D space.
    For a given user score vector `scores` and archetype signature
    `signature`, we compute:

        E = Σ_i w_i * (Δ_i^2)
          + λ * Σ_i w_i * |Δ_i|^1.5
          + ρ * R

    where:
        Δ_i = (scores[i] - signature[i]) / 100
        w_i = dimension weight (default = 1)
        λ   = curvature factor (nonlinearity)
        R   = normalized "rarity" of the archetype
              (based on overall trait height)
        ρ   = rarity_weight

    - Quadratic term keeps nearby points low-energy.
    - Curvature term adds non-linear "shape" to wells.
    - Rarity term can make very "extreme" archetypes slightly
      harder to fall into (Apex becomes special, not default).
    """

    if dim_weights is None:
        dim_weights = {}

    quad_term = 0.0
    curv_term = 0.0

    common_dims = set(scores.keys()) & set(signature.keys())

    if not common_dims:
        # If no overlap (should not happen with correct config),
        # return a very high energy.
        return float("inf")

    for d in common_dims:
        w = float(dim_weights.get(d, 1.0))
        # Normalise difference to [-1, 1] range
        diff = (scores[d] - signature[d]) / 100.0

        # Quadratic "spring" energy
        quad_term += w * (diff ** 2)

        # Curvature: gently exaggerates medium mismatches
        curv_term += w * (abs(diff) ** 1.5)

    base_energy = quad_term + lambda_curvature * curv_term

    # Archetype rarity: average signature level [0, 1]
    # Higher overall signatures => conceptually "rarer" states.
    sig_vals = [signature[d] for d in common_dims]
    if sig_vals:
        rarity = sum(sig_vals) / (len(sig_vals) * 100.0)
    else:
        rarity = 0.5

    energy = base_energy + rarity_weight * rarity

    return energy


def determine_archetype(scores, archetypes, dim_weights=None):
    """
    PUBLIC API — CHOOSE LOWEST-ENERGY ARCHETYPE

    Replaces simple Euclidean distance with an energy landscape approach.
    Returns:
        (best_name, best_data_dict)
    """

    best_name = None
    best_energy = float("inf")
    best_data = None

    for name, data in archetypes.items():
        signature = data.get("signature", {})
        if not signature:
            continue

        E = _compute_archetype_energy(
            scores=scores,
            signature=signature,
            dim_weights=dim_weights,
            lambda_curvature=0.6,
            rarity_weight=0.25,
        )

        if E < best_energy:
            best_energy = E
            best_name = name
            best_data = data

    return best_name, best_data


# ------------------------------------------------------------
# 3. MONTE CARLO STABILITY (UNCHANGED API)
# ------------------------------------------------------------

def monte_carlo_probabilities(
    base_scores,
    archetypes,
    runs=5000,
    noise=0.10,
    dim_weights=None,
):
    """
    Monte Carlo over the energy landscape.

    - Perturbs user scores with Gaussian noise (±10% default).
    - Re-classifies each sample via determine_archetype().
    - Estimates:
        - Probability distribution over archetypes
        - Identity stability (primary %)
        - Shadow archetype (2nd strongest)

    Returns:
        probs:   {archetype_name: probability%}
        stability: float (% of runs where primary appears)
        shadow: (name, probability%)
    """

    counts = {name: 0 for name in archetypes.keys()}

    for _ in range(runs):
        perturbed = {}

        for dim, val in base_scores.items():
            delta = random.gauss(0, noise * 100.0)
            perturbed_val = max(0.0, min(100.0, val + delta))
            perturbed[dim] = perturbed_val

        name, _ = determine_archetype(perturbed, archetypes, dim_weights=dim_weights)
        if name in counts:
            counts[name] += 1

    total = sum(counts.values()) or 1  # avoid divide-by-zero

    probs = {a: (c / total) * 100.0 for a, c in counts.items()}

    # Primary archetype = most frequent in simulation
    primary = max(probs, key=probs.get)
    stability = probs[primary]

    # Shadow archetype = 2nd highest probability
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    shadow = sorted_probs[1] if len(sorted_probs) > 1 else ("None", 0.0)

    return probs, stability, shadow


# ------------------------------------------------------------
# 4. DIAGNOSTIC: DISTANCE & ENERGY MATRICES
# ------------------------------------------------------------

def compute_archetype_distances(scores, archetypes, dim_weights=None):
    """
    Diagnostic helper. Returns BOTH:
      - 'euclidean': classic Euclidean distances
      - 'energy':    energy values from the landscape model

    Useful for debugging and visualisation.
    """

    euclid = {}
    energy = {}

    for name, data in archetypes.items():
        sig = data.get("signature", {})
        if not sig:
            continue

        common_dims = set(scores.keys()) & set(sig.keys())
        if not common_dims:
            euclid[name] = float("inf")
            energy[name] = float("inf")
            continue

        # Euclidean distance (for comparison)
        dist = math.sqrt(sum(
            (scores[d] - sig[d]) ** 2 for d in common_dims
        ))
        euclid[name] = dist

        # Energy via the same engine used in classification
        E = _compute_archetype_energy(
            scores=scores,
            signature=sig,
            dim_weights=dim_weights,
            lambda_curvature=0.6,
            rarity_weight=0.25,
        )
        energy[name] = E

    return {
        "euclidean": euclid,
        "energy": energy,
    }

