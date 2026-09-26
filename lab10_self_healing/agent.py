"""Lab 10: Ops Resilience - Validate, Diagnose, Fix.

This lightweight self-healing validation loop is intentionally aligned with the
Chapter 3 workflow: validate output, diagnose why it fails, repair only the
failing item, and re-run validation until the run is clean or the retry budget
is exhausted.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    candidate_id: str
    check: str
    passed: bool = False
    detail: str = ""


class ValidationReport(BaseModel):
    passed: bool = False
    issues: List[ValidationIssue] = Field(default_factory=list)
    diagnostics: List[str] = Field(default_factory=list)


class SelfHealingAgent:
    """Runs a validation loop, diagnoses failures, and repairs only the broken pieces."""

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().split())

    @staticmethod
    def _extract_relevant_sentence(text: str) -> str:
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
            normalized = SelfHealingAgent._normalize(sentence)
            if any(token in normalized for token in ["deadline", "submit", "approval", "review", "friday", "tomorrow", "wednesday"]):
                return sentence.strip()
        return text[:220].strip()

    @staticmethod
    def _find_grounding_source(candidate_text: str, threads: Iterable[Any]) -> Optional[Dict[str, Any]]:
        candidate_norm = SelfHealingAgent._normalize(candidate_text)
        for thread in threads:
            thread_text = "\n".join([
                thread.subject,
                thread.snippet,
                *[message.body for message in getattr(thread, "messages", [])],
            ])
            if candidate_norm in SelfHealingAgent._normalize(thread_text):
                return {
                    "source": "thread",
                    "source_id": thread.thread_id,
                    "grounding_text": SelfHealingAgent._extract_relevant_sentence(thread_text),
                    "tags": ["deadline", "approval", "faculty"],
                }
        return None

    @staticmethod
    def _fallback_source(threads: Iterable[Any]) -> Optional[Dict[str, Any]]:
        for thread in threads:
            thread_text = "\n".join([
                thread.subject,
                thread.snippet,
                *[message.body for message in getattr(thread, "messages", [])],
            ])
            if any(token in SelfHealingAgent._normalize(thread_text) for token in ["deadline", "submit", "approval", "review", "friday", "tomorrow", "wednesday"]):
                return {
                    "source": "thread",
                    "source_id": thread.thread_id,
                    "grounding_text": SelfHealingAgent._extract_relevant_sentence(thread_text),
                    "tags": ["deadline", "action", "faculty"],
                }
        return None

    def validate(self, candidates: Iterable[Dict[str, Any]]) -> ValidationReport:
        issues: List[ValidationIssue] = []
        diagnostics: List[str] = []

        for candidate in candidates:
            candidate_id = candidate.get("id", "unknown")
            item_status = candidate.get("status")
            grounded = bool(candidate.get("grounded"))
            source = candidate.get("source")
            reason = candidate.get("reason", "")

            if item_status == "rejected" or not grounded:
                issues.append(
                    ValidationIssue(
                        candidate_id=candidate_id,
                        check=f"{candidate_id}_grounded",
                        passed=False,
                        detail=f"Candidate {candidate_id} is not grounded in a valid in-scope source.",
                    )
                )
                diagnostics.append(f"{candidate_id}: rejected/ungrounded — {reason or 'missing evidence'}")

            if source in {None, "none", ""} and grounded:
                issues.append(
                    ValidationIssue(
                        candidate_id=candidate_id,
                        check=f"{candidate_id}_source",
                        passed=False,
                        detail=f"Candidate {candidate_id} is marked grounded but has no source record.",
                    )
                )
                diagnostics.append(f"{candidate_id}: grounded flag present without a source record")

        passed = not issues
        return ValidationReport(passed=passed, issues=issues, diagnostics=diagnostics)

    def repair_candidate(self, candidate: Dict[str, Any], source_threads: Iterable[Any]) -> Dict[str, Any]:
        candidate_id = candidate.get("id", "unknown")
        repaired = dict(candidate)

        source = self._find_grounding_source(candidate.get("candidate", candidate.get("content", "")), source_threads)
        if source is None:
            source = self._fallback_source(source_threads)

        if source is not None:
            repaired["candidate"] = source["grounding_text"]
            repaired["source"] = source["source"]
            repaired["source_id"] = source["source_id"]
            repaired["grounding_text"] = source["grounding_text"]
            repaired["tags"] = source["tags"]
            repaired["reason"] = f"Regenerated from {source['source']} {source['source_id']} after validation failure."
            repaired["status"] = "grounded"
            repaired["grounded"] = True
            return repaired

        repaired["source"] = "none"
        repaired["source_id"] = "none"
        repaired["grounding_text"] = ""
        repaired["tags"] = []
        repaired["reason"] = "No valid source found within the retry budget; candidate remains ungrounded."
        repaired["status"] = "rejected"
        repaired["grounded"] = False
        return repaired

    def heal(self, candidates: List[Dict[str, Any]], source_threads: Iterable[Any]) -> Dict[str, Any]:
        current = list(candidates)
        attempts = 0
        trace: List[str] = []

        while attempts < self.max_attempts:
            report = self.validate(current)
            if report.passed:
                return {
                    "passed": True,
                    "attempts": attempts + 1,
                    "report": report,
                    "final_candidates": current,
                    "trace": trace,
                }

            failing_ids = {issue.candidate_id for issue in report.issues}
            trace.append(f"Attempt {attempts + 1} validation failed for: {sorted(failing_ids)} — {report.diagnostics}")
            repaired: List[Dict[str, Any]] = []
            for candidate in current:
                candidate_id = candidate.get("id", "unknown")
                if candidate_id not in failing_ids:
                    repaired.append(candidate)
                    trace.append(f"{candidate_id}: skipped, already valid")
                    continue

                repaired_candidate = self.repair_candidate(candidate, source_threads)
                repaired.append(repaired_candidate)
                trace.append(f"{candidate_id}: regenerated from {repaired_candidate.get('source_id', 'none')} after validation failure")

            current = repaired
            attempts += 1

        final_report = self.validate(current)
        return {
            "passed": final_report.passed,
            "attempts": attempts,
            "report": final_report,
            "final_candidates": current,
            "trace": trace,
        }


def run_self_healing_check(candidates: List[Dict[str, Any]], threads: Iterable[Any], max_attempts: int = 3) -> Dict[str, Any]:
    """Convenience wrapper for demo and validation scripts."""
    return SelfHealingAgent(max_attempts=max_attempts).heal(candidates, threads)
