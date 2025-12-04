import math
import random

# ============================================================
# 1. NORMALISE RAW QUESTION SCORES (1–5 → 0–100)
# ============================================================

def normalize_scores(raw_answers):
    """
    raw_answers = {
        qid: {"value": int(1–5), "dimension": "thinking", "reverse": bool}
    }
    """
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

        # Reverse-coded questions: 1 ↔ 5
        if info.get("reverse", False):
            val = 6 - val

        dims[info["dimension"]].append(val)

    final_scores = {}
    for dim, values in dims.items():
        if not values:
            final_scores[dim] = 0
        else:
            avg = sum(values) / len(values)
            final_scores[dim] = ((avg - 1) / 4) * 100   # 0–100 scale

    return final_scores


# ============================================================
# 2. ARCHETYPE MATCHING (EUCLIDEAN DISTANCE)
# ============================================================

def determine_archetype(scores, archetypes):
    """
    scores = {"thinking": 55, "execution": 62, ... }
    archetypes = { "Visionary": {signature: {...}}, ... }
    """
    best_name = None
    best_dist = float("inf")
    best_data = None

    for name, data in archetypes.items():
        signature = data.get("signature", {})

        dims = set(scores.keys()) & set(signature.keys())
        if not dims:
            continue

        dist = math.sqrt(sum((scores[d] - signature[d]) ** 2 for d in dims))

        if dist < best_dist:
            best_dist = dist
            best_name = name
            best_data = data

    return best_name, best_data


# ============================================================
# 3. MONTE CARLO SIMULATION (PRIMARY + SHADOW ARCHETYPE)
# ============================================================

def monte_carlo_probabilities(base_scores, archetypes, runs=5000, noise=0.07):
    """
    Monte Carlo stability testing.
    noise=0.07 → ±7% variation on 0–100 scale.
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

    primary = max(probs, key=probs.get)
    stability = probs[primary]

    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
    shadow = sorted_probs[1] if len(sorted_probs) > 1 else ("None", 0)

    return probs, stability, shadow


# ============================================================
# 4. OPTIONAL DIAGNOSTIC (FOR DEBUGGING)
# ============================================================

def compute_archetype_distances(scores, archetypes):
    """
    Returns raw Euclidean distances to all archetypes.
    Makes debugging much easier.
    """
    distances = {}
    for name, data in archetypes.items():
        sig = data["signature"]
        dims = set(scores.keys()) & set(sig.keys())
        dist = math.sqrt(sum((scores[d] - sig[d]) ** 2 for d in dims))
        distances[name] = dist

    return distances

    return distances
