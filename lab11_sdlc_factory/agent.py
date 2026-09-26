"""Lab 11: SDLC Factory — Spec → Tested Output.

This lab treats the locked plan as a spec and prevents any triaged inbox with
pending draft replies from advancing to the mailbox owner unless the automated
acceptance suite has passed.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field


class AcceptanceResult(BaseModel):
    passed: bool = False
    checks: List[Dict[str, Any]] = Field(default_factory=list)
    details: List[str] = Field(default_factory=list)
    report: str = ""


class SDLCFactory:
    """Build an artifact from the spec, then validate it before human review."""

    @staticmethod
    def build_artifact(plan: Dict[str, Any], drafts: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        artifact: List[Dict[str, Any]] = []
        for draft in drafts:
            artifact.append({
                "id": draft["id"],
                "subject": draft["subject"],
                "status": draft.get("status", "draft"),
                "source_id": draft.get("source_id", "unknown"),
                "evidence": draft.get("evidence", ""),
                "grounded": bool(draft.get("grounded", False)),
            })
        return artifact

    @staticmethod
    def validate_artifact(artifact: Iterable[Dict[str, Any]], plan: Dict[str, Any]) -> AcceptanceResult:
        checks: List[Dict[str, Any]] = [
            {"name": "plan_locked", "passed": True, "detail": "Plan was locked before the build began."},
            {"name": "artifact_present", "passed": True, "detail": "Artifact contains draft items."},
            {"name": "draft_status", "passed": True, "detail": "Draft items are in draft status."},
            {"name": "grounded_source", "passed": True, "detail": "Each draft has a grounded source and evidence-backed claim."},
            {"name": "evidence_recorded", "passed": True, "detail": "Each draft includes evidence text."},
            {"name": "human_gate_ready", "passed": True, "detail": "Artifact is ready for human review; all gate checks are green."},
        ]
        details: List[str] = []
        passed = True

        artifact_list = list(artifact)
        required_fields = {"id", "subject", "status", "source_id", "evidence", "grounded"}

        if not artifact_list:
            checks[1]["passed"] = False
            checks[1]["detail"] = "No draft items were produced for the acceptance gate."
            details.append("No draft items were produced for the acceptance gate.")
            passed = False
        else:
            checks[1]["passed"] = True
            checks[1]["detail"] = f"Artifact contains {len(artifact_list)} draft items."

        if plan.get("locked") is not True:
            checks[0]["passed"] = False
            checks[0]["detail"] = "Plan is not locked; spec was not frozen before build."
            details.append("Plan is not locked; spec was not frozen before build.")
            passed = False

        for item in artifact_list:
            missing = required_fields - set(item.keys())
            if missing:
                passed = False
                details.append(f"{item.get('id', 'unknown')}: missing required fields {sorted(missing)}")
                continue

            if item.get("status") != "draft":
                passed = False
                checks[2]["passed"] = False
                checks[2]["detail"] = f"{item.get('id', 'unknown')}: status must be draft before human review"
                details.append(f"{item.get('id', 'unknown')}: status must be draft before human review")

            if not item.get("grounded"):
                passed = False
                checks[3]["passed"] = False
                checks[3]["detail"] = f"{item.get('id', 'unknown')}: no evidence-backed source"
                details.append(f"{item.get('id', 'unknown')}: no evidence-backed source")

            if not item.get("evidence"):
                passed = False
                checks[4]["passed"] = False
                checks[4]["detail"] = f"{item.get('id', 'unknown')}: no evidence text recorded"
                details.append(f"{item.get('id', 'unknown')}: no evidence text recorded")

        if all(check["passed"] for check in checks[:5]):
            checks[5]["passed"] = True
            checks[5]["detail"] = "Artifact is ready for human review; all gate checks are green."
        else:
            checks[5]["passed"] = False
            checks[5]["detail"] = "Artifact did not pass the acceptance gate and is blocked from human review."
            details.append("Artifact did not pass the acceptance gate and is blocked from human review.")
            passed = False

        if passed:
            details.insert(0, "All acceptance checks passed: artifact matches the spec and is gated for human review.")

        report = "\n".join(details) if details else "Acceptance suite passed with no issues."
        return AcceptanceResult(passed=passed, checks=checks, details=details, report=report)

    @staticmethod
    def build_and_validate(plan: Dict[str, Any], drafts: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        artifact = SDLCFactory.build_artifact(plan, drafts)
        report = SDLCFactory.validate_artifact(artifact, plan)
        return {
            "plan": plan,
            "artifact": artifact,
            "acceptance_report": report,
            "gate_passed": report.passed,
        }


def run_sdlc_factory(plan: Dict[str, Any], drafts: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience wrapper for demo and validation scripts."""
    return SDLCFactory.build_and_validate(plan, drafts)
