"""
filtering/filter_engine.py
--------------------------
Rule-based foundation layer for the College Admission Assistance Agent.

STRICT RULE : No LLMs, no APIs, no RAG.
COMPATIBILITY: Pure Python 3.14 stdlib only — no compiled DLL extensions.

Data model: each "row" is a plain dict with keys matching the CSV headers.
  load_college_data()      -> list[dict]   (replaces pd.read_csv)
  clean_college_data()     -> list[dict]   (replaces DataFrame cleaning)
  apply_hard_filters()     -> list[dict]   (replaces boolean-mask filtering)
"""

import csv
import math


# ---------------------------------------------------------------------------
# Expected columns
# ---------------------------------------------------------------------------
_REQUIRED_COLUMNS = {
    "college_id",
    "college_name",
    "state",
    "city",
    "exam_accepted",
    "closing_rank",
    "annual_fees_inr",
}

_STRING_STRIP_COLS = ("state", "city", "exam_accepted")


# ---------------------------------------------------------------------------
# Helper — load CSV (replaces pd.read_csv)
# ---------------------------------------------------------------------------

def load_college_data(filepath: str) -> list[dict]:
    """
    Load a college CSV into a list of dicts using stdlib csv.DictReader.

    Parameters
    ----------
    filepath : str
        Absolute or relative path to the CSV file.

    Returns
    -------
    list[dict]
        Each dict represents one row; keys are the CSV header names.
    """
    with open(filepath, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [row for row in reader]


# ---------------------------------------------------------------------------
# Helper — safe numeric coercion
# ---------------------------------------------------------------------------

def _to_int_or_none(value: str) -> int | None:
    """Return int if *value* is a non-empty, non-NaN string; else None."""
    if value is None:
        return None
    stripped = str(value).strip()
    if stripped == "" or stripped.lower() in ("nan", "none", "null"):
        return None
    try:
        # Handle float strings like "450000.0"
        return int(float(stripped))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 1. Data Cleaning
# ---------------------------------------------------------------------------

def clean_college_data(data: list[dict]) -> list[dict]:
    """
    Clean and standardize raw college data loaded from a CSV.

    Steps performed:
      - Validate that all expected columns are present.
      - Drop rows where ``closing_rank`` or ``annual_fees_inr`` are missing /
        blank / NaN.
      - Convert ``closing_rank`` and ``annual_fees_inr`` to int.
      - Strip leading/trailing whitespace from ``state``, ``city``,
        and ``exam_accepted``.
      - Upper-case ``exam_accepted`` for standardized downstream matching.

    Parameters
    ----------
    data : list[dict]
        Raw rows, typically from :func:`load_college_data`.

    Returns
    -------
    list[dict]
        Cleaned rows (rows that fail validation are silently dropped).

    Raises
    ------
    ValueError
        If any expected column is missing from the first row.
    """
    if not data:
        return []

    # --- Column validation (check first row's keys) --------------------------
    missing = _REQUIRED_COLUMNS - set(data[0].keys())
    if missing:
        raise ValueError(
            f"Required columns missing from data: {sorted(missing)}"
        )

    cleaned: list[dict] = []

    for row in data:
        # --- Parse critical numeric fields -----------------------------------
        closing_rank   = _to_int_or_none(row.get("closing_rank"))
        annual_fees    = _to_int_or_none(row.get("annual_fees_inr"))

        # Drop rows where either numeric field is absent
        if closing_rank is None or annual_fees is None:
            continue

        # --- Build cleaned row (copy so original is not mutated) -------------
        cleaned_row = dict(row)

        cleaned_row["closing_rank"]   = closing_rank
        cleaned_row["annual_fees_inr"] = annual_fees

        # --- String normalization --------------------------------------------
        for col in _STRING_STRIP_COLS:
            val = cleaned_row.get(col) or ""
            cleaned_row[col] = val.strip()

        cleaned_row["exam_accepted"] = cleaned_row["exam_accepted"].upper()

        cleaned.append(cleaned_row)

    return cleaned


# ---------------------------------------------------------------------------
# 2. Hard Filters
# ---------------------------------------------------------------------------

def apply_hard_filters(
    data: list[dict],
    user_preferences: dict,
) -> list[dict]:
    """
    Apply strict, rule-based hard filters to cleaned college data.

    Filter logic:

    1. **Budget**  — keep rows where ``annual_fees_inr`` <=
       ``user_preferences['budget']``.
    2. **Exam**    — keep rows where ``exam_accepted`` exactly matches
       ``user_preferences['exam']`` (case-insensitive).
    3. **Location**— if ``user_preferences['states']`` is a non-empty list,
       keep rows whose ``state`` is in that list; otherwise skip this filter.

    Parameters
    ----------
    data : list[dict]
        Cleaned rows from :func:`clean_college_data`.
    user_preferences : dict
        Keys expected:

        - ``"budget"``  (*int*)       : Max annual fees in INR.
        - ``"exam"``    (*str*)       : Entrance exam name, e.g. ``"JEE MAIN"``.
        - ``"states"``  (*list[str]*) : Preferred states; empty list = no filter.

    Returns
    -------
    list[dict]
        Filtered rows. May be empty if no college satisfies all constraints.

    Raises
    ------
    KeyError
        If ``"budget"``, ``"exam"``, or ``"states"`` are missing from
        ``user_preferences``.
    """
    budget: int  = user_preferences["budget"]
    exam:   str  = user_preferences["exam"].strip().upper()
    states: list = user_preferences["states"]

    # Build a set for O(1) membership checks (important for large datasets)
    states_set: set[str] = set(states) if states else set()

    result: list[dict] = []

    for row in data:
        # Filter 1: Budget
        if row["annual_fees_inr"] > budget:
            continue

        # Filter 2: Exam (case-insensitive exact match)
        if row["exam_accepted"] != exam:
            continue

        # Filter 3: Location (skipped when states list is empty)
        if states_set and row["state"] not in states_set:
            continue

        result.append(row)

    return result
