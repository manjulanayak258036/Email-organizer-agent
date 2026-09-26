"""Lab 10 acceptance script: Ops Resilience — Validate, Diagnose, Fix."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab02_tools.tools import SAMPLE_FACULTY_THREADS
from lab10_self_healing.agent import run_self_healing_check


def main() -> None:
    print("=" * 75)
    print("LAB 10: Ops Resilience - Validate, Diagnose, Fix")
    print("=" * 75)
    print("Command to run: python lab10_self_healing/demo_lab10.py")

    candidates = [
        {
            "id": "cand_101",
            "status": "rejected",
            "source": "none",
            "source_id": "none",
            "grounded": False,
            "candidate": "The moon landing memo is required by the dean before Friday.",
            "reason": "No in-scope source matched closely enough; strongest overlap was ['before'] (14%) but this was below the grounding threshold.",
        },
        {
            "id": "cand_102",
            "status": "grounded",
            "source": "thread",
            "source_id": "th_002_dean_curriculum",
            "grounded": True,
            "candidate": "Please submit all revised course syllabi and laboratory safety checklists by tomorrow, Wednesday at 3:00 PM.",
            "reason": "Matched exact wording in thread th_002_dean_curriculum; the claim is supported by the source text.",
        },
    ]

    result = run_self_healing_check(candidates, SAMPLE_FACULTY_THREADS, max_attempts=3)

    print("\nValidation trace:")
    for trace in result["trace"]:
        print(f"- {trace}")

    print("\nFinal candidates:")
    for candidate in result["final_candidates"]:
        print(f"- {candidate['id']} | status={candidate['status']} | source={candidate['source']}:{candidate['source_id']} | grounded={candidate['grounded']} | reason={candidate['reason']}")

    print(f"\nAttempts: {result['attempts']}")
    print(f"Final validation passed: {result['passed']}")

    assert result["passed"] is True
    assert result["attempts"] <= 3
    assert all(item["grounded"] for item in result["final_candidates"])
    assert all(item["status"] == "grounded" for item in result["final_candidates"])
    assert any("cand_102: skipped, already valid" in step for step in result["trace"]) 
    assert all(candidate["id"] != "cand_102" or candidate["source_id"] == "th_002_dean_curriculum" for candidate in result["final_candidates"])

    print("\n[ACCEPTANCE PASS] Validation diagnosed the failing candidate, regenerated only the broken item, and the final run passed within the retry budget.")


if __name__ == "__main__":
    main()
