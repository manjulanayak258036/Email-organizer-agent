"""Lab 11 acceptance script: SDLC Factory — Spec → Tested Output."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab11_sdlc_factory.agent import run_sdlc_factory


def main() -> None:
    print("=" * 75)
    print("LAB 11: SDLC Factory - Spec → Tested Output")
    print("=" * 75)
    print("Command to run: python lab11_sdlc_factory/demo_lab11.py")

    plan = {
        "name": "faculty_email_triage_build",
        "locked": True,
        "steps": [
            "classify threads",
            "score urgency",
            "ground drafts",
            "validate acceptance gate",
            "present to mailbox owner"
        ],
    }

    passing_drafts = [
        {
            "id": "draft_101",
            "subject": "Thesis committee form review",
            "status": "draft",
            "source_id": "th_001_grad_thesis",
            "evidence": "The graduate school deadline for submitting the signed thesis defense committee form is this Friday at 5:00 PM.",
            "grounded": True,
        },
        {
            "id": "draft_102",
            "subject": "Curriculum revisions follow-up",
            "status": "draft",
            "source_id": "th_002_dean_curriculum",
            "evidence": "Please submit all revised course syllabi and laboratory safety checklists by tomorrow, Wednesday at 3:00 PM.",
            "grounded": True,
        },
    ]

    failing_drafts = [
        {
            "id": "draft_999",
            "subject": "Moon landing memo",
            "status": "draft",
            "source_id": "none",
            "evidence": "",
            "grounded": False,
        }
    ]

    print("\n-- PASSING PATH --")
    passing_result = run_sdlc_factory(plan, passing_drafts)
    passing_report = passing_result["acceptance_report"]
    print("Acceptance report:")
    print(passing_report.report)
    print(f"PASS: {passing_report.passed}")
    for check in passing_report.checks:
        print(f"- {check['name']}: {'PASS' if check['passed'] else 'FAIL'} | {check['detail']}")

    assert passing_result["gate_passed"] is True
    assert passing_report.passed is True
    assert all(item["status"] == "draft" for item in passing_result["artifact"])
    assert all(item["grounded"] is True for item in passing_result["artifact"])

    print("\n-- FAILING PATH --")
    failing_result = run_sdlc_factory(plan, failing_drafts)
    failing_report = failing_result["acceptance_report"]
    print("Blocked artifact report:")
    print(failing_report.report)
    print(f"PASS: {failing_report.passed}")
    for check in failing_report.checks:
        print(f"- {check['name']}: {'PASS' if check['passed'] else 'FAIL'} | {check['detail']}")

    assert failing_result["gate_passed"] is False
    assert failing_report.passed is False
    assert any(check["name"] == "grounded_source" and not check["passed"] for check in failing_report.checks)

    print("\n[ACCEPTANCE PASS] The suite reports each named gate check individually, and the failing artifact is blocked before human review as required by the Lab 11 pitfall.")


if __name__ == "__main__":
    main()
