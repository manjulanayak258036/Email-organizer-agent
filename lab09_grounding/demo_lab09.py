"""Lab 9 acceptance script: Deep Research — Ground & Evidence."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab02_tools.tools import SAMPLE_FACULTY_THREADS
from lab09_grounding.agent import run_grounding_check


def main() -> None:
    print("=" * 75)
    print("LAB 9: Deep Research - Ground & Evidence")
    print("=" * 75)

    prior_replies = [
        "The graduate school deadline for submitting the signed thesis defense committee form is this Friday at 5:00 PM.",
        "Please submit all revised course syllabi and laboratory safety checklists by tomorrow, Wednesday at 3:00 PM.",
        "I am available during office hours at 2:30 PM for a quick 10-minute check.",
    ]

    candidates = [
        {"id": "cand_001", "content": "The graduate school deadline for submitting the signed thesis defense committee form is this Friday at 5:00 PM."},
        {"id": "cand_002", "content": "Please submit all revised course syllabi and laboratory safety checklists by tomorrow, Wednesday at 3:00 PM."},
        {"id": "cand_003", "content": "A moon landing memo is required by the dean before Friday."},
    ]

    report = run_grounding_check(SAMPLE_FACULTY_THREADS, candidates, prior_replies=prior_replies)

    print("Grounded candidates:")
    for candidate_id in report.grounded:
        print(f"- {candidate_id}")
    print("Rejected candidates:")
    for candidate_id in report.rejected:
        print(f"- {candidate_id}")

    print("\nEvidence Table")
    print(f"{'candidate':<12} | {'status':<9} | {'source':<12} | {'scope':<12} | {'tags':<25} | {'grounding_text'}")
    print("-" * 150)
    for evidence in report.evidence_table:
        tags = ", ".join(evidence["tags"]) if evidence["tags"] else "-"
        ground_text = evidence["grounding_text"][:90].replace("\n", " ")
        print(f"{evidence['candidate_id']:<12} | {evidence['status']:<9} | {evidence['source']:<12} | {evidence['scope']:<12} | {tags:<25} | {ground_text}")
        print(f"  reason: {evidence['explanation']}")

    assert report.grounded == ["cand_001", "cand_002"]
    assert report.rejected == ["cand_003"]
    assert all(item["in_scope"] for item in report.evidence_table if item["candidate_id"] in {"cand_001", "cand_002"})
    assert not any(item["in_scope"] for item in report.evidence_table if item["candidate_id"] == "cand_003")
    assert any("No in-scope" in item["explanation"] for item in report.evidence_table if item["candidate_id"] == "cand_003")

    print("\n[ACCEPTANCE PASS] Every grounded output maps to an in-scope source; the ungrounded candidate was rejected with an explicit explanation.")


if __name__ == "__main__":
    main()
