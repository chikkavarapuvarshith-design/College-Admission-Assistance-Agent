"""
filtering/ranking_engine.py
---------------------------
College classification / bucketing layer for the College Admission Agent.

STRICT RULE : No LLMs, no external libraries.
             Pure Python 3.14 stdlib — consistent with filter_engine.py.

Business Logic (LOWER rank number == BETTER):
  margin      = closing_rank * margin_pct          (default 15 %)
  safe_bound  = closing_rank - margin
  dream_bound = closing_rank + margin

  SAFE         : student_rank <= safe_bound         (overqualified)
  TARGET       : safe_bound   <  student_rank <= closing_rank  (realistic)
  DREAM        : closing_rank <  student_rank <= dream_bound   (stretch)
  OUT OF REACH : student_rank >  dream_bound        (excluded from output)
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_colleges(
    filtered_data: list[dict],
    student_rank: int,
    margin_pct: float = 0.15,
) -> dict[str, list[dict]]:
    """
    Classify pre-filtered colleges into SAFE / TARGET / DREAM buckets.

    Parameters
    ----------
    filtered_data : list[dict]
        Output of ``apply_hard_filters()`` from *filter_engine.py*.
        Each dict must contain at least ``closing_rank`` (int) and
        ``annual_fees_inr`` (int).
    student_rank : int
        The student's entrance-exam rank. Lower is better (rank 1 > rank 10 000).
    margin_pct : float, optional
        Fractional margin around ``closing_rank`` used for bucket boundaries.
        Default is ``0.15`` (15 %).

    Returns
    -------
    dict
        Strictly formatted output::

            {
                "dream_colleges":  [ {college_dict}, ... ],   # sorted by fees ↑
                "target_colleges": [ {college_dict}, ... ],
                "safe_colleges":   [ {college_dict}, ... ],
            }

        OUT OF REACH colleges are silently excluded.
        Each list is sorted by ``annual_fees_inr`` ascending.

    Raises
    ------
    ValueError
        If ``student_rank`` is not a positive integer or ``margin_pct``
        is not in the range (0, 1).
    """
    # --- Input validation ----------------------------------------------------
    if not isinstance(student_rank, int) or student_rank < 1:
        raise ValueError(f"student_rank must be a positive integer, got {student_rank!r}.")
    if not (0 < margin_pct < 1):
        raise ValueError(f"margin_pct must be between 0 and 1 (exclusive), got {margin_pct}.")

    dream:  list[dict] = []
    target: list[dict] = []
    safe:   list[dict] = []

    for row in filtered_data:
        closing_rank: int = row["closing_rank"]

        # Compute bounds
        margin: float      = closing_rank * margin_pct
        safe_bound: float  = closing_rank - margin   # below closing_rank
        dream_bound: float = closing_rank + margin   # above closing_rank

        # Convert row to a plain dict (already is one, but copy defensively)
        college: dict = dict(row)

        # --- Bucketing logic -------------------------------------------------
        if student_rank <= safe_bound:
            # Student is clearly overqualified — guaranteed admission territory
            safe.append(college)

        elif safe_bound < student_rank <= closing_rank:
            # Realistic match — within the competitive zone
            target.append(college)

        elif closing_rank < student_rank <= dream_bound:
            # Stretch — possible in later counseling rounds / vacancies
            dream.append(college)

        # else: student_rank > dream_bound → OUT OF REACH, excluded silently

    # --- Sort each bucket by annual_fees_inr ascending -----------------------
    _sort_key = lambda c: c["annual_fees_inr"]

    return {
        "dream_colleges":  sorted(dream,  key=_sort_key),
        "target_colleges": sorted(target, key=_sort_key),
        "safe_colleges":   sorted(safe,   key=_sort_key),
    }
