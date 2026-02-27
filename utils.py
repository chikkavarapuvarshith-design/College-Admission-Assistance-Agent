"""
backend/utils.py
----------------
Orchestrator layer for the College Admission Assistance Agent.

Ties together:
  filtering.filter_engine   — data loading, cleaning, hard filtering
  filtering.ranking_engine  — SAFE / TARGET / DREAM classification

Intended audience: frontend and LLM layer team members.
All errors are returned as dicts (never raised) so callers get a
consistent contract regardless of what goes wrong.

NOTE: Pandas is not used here because the project targets Python 3.14,
where Pandas' compiled DLLs are blocked by the system Application
Control policy. `load_college_data` (csv.DictReader) is the drop-in
replacement for pd.read_csv — same interface, zero native extensions.
"""

import sys
import pathlib

# ---------------------------------------------------------------------------
# Ensure the project root (scratch/) is on sys.path so that the `filtering`
# package is importable regardless of where Python is launched from.
# (Fixes VS Code "Run Python File" which sets cwd to the file's own folder.)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent  # backend/ → scratch/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from filtering.filter_engine import (
    load_college_data,
    clean_college_data,
    apply_hard_filters,
)
from filtering.ranking_engine import classify_colleges


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_recommendations(
    csv_path: str,
    student_payload: dict,
) -> dict:
    """
    End-to-end pipeline: load → clean → filter → classify.

    Parameters
    ----------
    csv_path : str
        Path to the ``colleges.csv`` database file.
    student_payload : dict
        Must contain:

        - ``"budget"`` (*int*)       : Max annual fees in INR.
        - ``"states"`` (*list[str]*) : Preferred states; empty = no filter.
        - ``"exam"``   (*str*)       : Entrance exam, e.g. ``"JEE MAIN"``.
        - ``"rank"``   (*int*)       : Student's entrance-exam rank (lower = better).

    Returns
    -------
    dict
        On success — the classification contract::

            {
                "dream_colleges":  [ {college_dict}, ... ],
                "target_colleges": [ {college_dict}, ... ],
                "safe_colleges":   [ {college_dict}, ... ],
            }

        On failure — an error envelope::

            {"error": "<human-readable message>"}
    """
    # ------------------------------------------------------------------
    # Step 1 — Load CSV (graceful FileNotFoundError handling)
    # ------------------------------------------------------------------
    try:
        raw_data = load_college_data(csv_path)
    except FileNotFoundError:
        return {"error": "Database not found."}
    except Exception as exc:                        # malformed path, permissions, etc.
        return {"error": f"Failed to load database: {exc}"}

    # ------------------------------------------------------------------
    # Step 2 — Clean (drop bad rows, normalise types & strings)
    # ------------------------------------------------------------------
    try:
        cleaned_data = clean_college_data(raw_data)
    except ValueError as exc:
        return {"error": f"Data schema error: {exc}"}

    # ------------------------------------------------------------------
    # Step 3 — Hard filters (budget / exam / location)
    # ------------------------------------------------------------------
    try:
        user_prefs = {
            "budget": student_payload["budget"],
            "states": student_payload["states"],
            "exam":   student_payload["exam"],
        }
        filtered_data = apply_hard_filters(cleaned_data, user_prefs)
    except KeyError as exc:
        return {"error": f"Missing field in student_payload: {exc}"}

    # ------------------------------------------------------------------
    # Step 4 — Classify into SAFE / TARGET / DREAM buckets
    # ------------------------------------------------------------------
    try:
        result = classify_colleges(filtered_data, student_rank=student_payload["rank"])
    except (KeyError, ValueError) as exc:
        return {"error": f"Classification failed: {exc}"}

    # ------------------------------------------------------------------
    # Step 5 — Return the final contract
    # ------------------------------------------------------------------
    return result
