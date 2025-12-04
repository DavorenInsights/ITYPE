import csv
import os
from datetime import datetime


CSV_PATH = "data/responses.csv"


def ensure_csv_exists():
    """
    Creates the CSV with headers if it does not exist.
    """
    if not os.path.exists("data"):
        os.makedirs("data")

    if not os.path.isfile(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "final_archetype",
                "stability",
                "shadow_archetype",
                "thinking",
                "execution",
                "risk",
                "motivation",
                "team",
                "commercial",
                "raw_answers_json"
            ])


def log_response(final_archetype, stability, shadow, scores, raw_answers):
    """
    Logs a completed test entry.

    Parameters:
        final_archetype : str
        stability : float
        shadow : (str, float)
        scores : dict of final dimension scores
        raw_answers : dict of original question responses
    """

    ensure_csv_exists()

    shadow_name, shadow_pct = shadow

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.utcnow().isoformat(),
            final_archetype,
            round(stability, 2),
            f"{shadow_name} ({round(shadow_pct, 2)}%)",
            scores.get("thinking", 0),
            scores.get("execution", 0),
            scores.get("risk", 0),
            scores.get("motivation", 0),
            scores.get("team", 0),
            scores.get("commercial", 0),
            str(raw_answers)  # can be used later for PCA / reliability
        ])
