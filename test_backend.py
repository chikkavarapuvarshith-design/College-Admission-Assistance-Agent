"""
test_backend.py
---------------
Quick smoke-test for the full pipeline:
  load → clean → filter → classify

Run from the project root (scratch/):
    python test_backend.py
"""

from backend.utils import get_recommendations

# --- Sample student payload --------------------------------------------------
student_payload = {
    "budget": 500000,                          # max annual fees
    "states": ["Maharashtra", "Karnataka"],    # preferred states
    "exam":   "JEE MAIN",                      # accepted exam
    "rank":   12000,                           # student's rank
}

result = get_recommendations("data/colleges.csv", student_payload)

# --- Pretty-print results ----------------------------------------------------
if "error" in result:
    print("ERROR:", result["error"])
else:
    for bucket in ("dream_colleges", "target_colleges", "safe_colleges"):
        colleges = result[bucket]
        print(f"\n{'='*40}")
        print(f"  {bucket.upper().replace('_', ' ')}  ({len(colleges)} found)")
        print(f"{'='*40}")
        if not colleges:
            print("  (none)")
        for c in colleges:
            print(f"  {c['college_name']:30s}  rank={c['closing_rank']:<8}  fees=INR {c['annual_fees_inr']:,}")

print("\nDone.")
