import numpy as np


# ============================================================
# DIMENSION CHECK
# ============================================================

CORE_DIMENSIONS = [
    "thinking",
    "execution",
    "risk",
    "motivation",
    "team",
    "commercial",
]


def _validate_archetype_vector(vec):
    """Ensure archetype has all required fields and returns a clean vector."""
    return np.array([float(vec.get(dim, 0.0)) for dim in CORE_DIMENSIONS])


# ============================================================
# SCORE NORMALISATION
# ============================================================

def normalize_scores(answers):
    """
    Convert raw Likert answers (1–5) into clean 0–100 dimension scores.
    Reverse-scored items are handled automatically.

    answers = {
        "question text": { "value": x, "dimension": "thinking", "reverse": False }
    }
    """
    dimension_totals = {dim: [] for dim in CORE_DIMENSIONS}

    for q, meta in answers.items():
        val = meta.get("value", 3)
        dim = meta.get("dimension", "thinking")
        reverse = meta.get("reverse", False)

        if reverse:
            val = 6 - val  # reverse scoring: 1→5, 5→1

        if dim in dimension_totals:
            dimension_totals[dim].append(val)

    # Average + scale to 0–100
    final_scores = {}
    for dim, vals in dimension_totals.items():
        if len(vals) == 0:
            final_scores[dim] = 50.0
        else:
            avg = sum(vals) / len(vals)
            final_scores[dim] = (avg - 1) / 4 * 100

    return final_scores


# ============================================================
# ARCHETYPE MATCHING
# ============================================================

def determine_archetype(final_scores, archetypes):
    """
    Given 6D score vector and all archetypes, return the closest one.
    Uses Euclidean distance.
    """
    user_vec = np.array([final_scores[d] for d in CORE_DIMENSIONS])

    best_name = None
    best_dist = float("inf")

    for name, data in archetypes.items():
        vec = _validate_archetype_vector(data.get("vector", {}))
        dist = np.linalg.norm(user_vec - vec)

        if dist < best_dist:
            best_dist = dist
            best_name = name

    return best_name, archetypes.get(best_name, {})


# ============================================================
# DISTANCE → ENERGY SCORE TRANSFORM
# ============================================================

def _distance_to_energy(distance, temp=60.0):
    """
    Convert archetype distance to energy weight.
    Lower distance → higher weight.

    temp controls softness (lower → sharper identity)
    """
    return np.exp(-distance / temp)


# ============================================================
# MONTE CARLO IDENTITY SIMULATION
# ============================================================

def monte_carlo_probabilities(final_scores, archetypes, trials=4000, noise=4.0):
    """
    Simulate many noisy versions of the score vector.
    Each simulation selects an archetype → identity probabilities.

    noise controls perturbation size.
    """
    user_vec = np.array([final_scores[d] for d in CORE_DIMENSIONS])

    arche_vecs = {
        name: _validate_archetype_vector(data.get("vector", {}))
        for name, data in archetypes.items()
    }

    counts = {name: 0 for name in archetypes}

    names = list(archetypes.keys())
    A = len(names)

    for _ in range(trials):
        noisy_vec = user_vec + np.random.normal(0, noise, size=len(CORE_DIMENSIONS))

        # find closest archetype
        best_name = None
        best_dist = float("inf")

        for name in names:
            dist = np.linalg.norm(noisy_vec - arche_vecs[name])
            if dist < best_dist:
                best_dist = dist
                best_name = name

        counts[best_name] += 1

    # convert counts → probabilities
    probs = {k: (v / trials) * 100 for k, v in counts.items()}

    # stability = how strongly the primary archetype dominates
    primary_name = max(probs, key=probs.get)
    stability = probs[primary_name]

    # shadow = second-highest
    shadow_name = sorted(probs.items(), key=lambda x: x[1], reverse=True)[1]

    return probs, stability, shadow_name


# ============================================================
# CLEAN ARCHETYPE ENERGY REPORT (OPTIONAL)
# ============================================================

def compute_archetype_distances(final_scores, archetypes):
    """
    Returns both Euclidean distances and energy weights.
    Useful for debug or future analytics.
    """
    user_vec = np.array([final_scores[d] for d in CORE_DIMENSIONS])

    dist_out = {}
    energy_out = {}

    for name, data in archetypes.items():
        vec = _validate_archetype_vector(data.get("vector", {}))
        dist = np.linalg.norm(user_vec - vec)

        dist_out[name] = dist
        energy_out[name] = _distance_to_energy(dist)

    return {
        "euclidean": dist_out,
        "energy": energy_out
    }
