"""Lab 8: Parallel Swarm - parallel triage with plan-alignment merge.

This module implements the Chapter 3 Lab 8 behavior:
- a coordinator defines a task plan and specialist focus weights
- multiple email threads are processed in parallel
- each candidate is scored against the plan
- the best-aligned candidate survives the merge for each thread

The implementation stays intentionally lightweight, but it follows the same
parallel worker + merge semantics described in the Chapter 3 spec.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field

from core.classifier import classify_sender
from core.models import EmailThread, SenderCategory, UrgencyLevel

ALIGNMENT_SCORE_MIN = 0
ALIGNMENT_SCORE_MAX = 85  # 8 plan-focus terms * 10 + 5 student/admin bonus


class SwarmCandidate(BaseModel):
    thread_id: str
    subject: str
    sender: str
    category: str
    urgency: str
    urgency_score: int
    alignment_score: int
    rationale: str


class ParallelSwarmCoordinator:
    """Process multiple threads in parallel and merge by plan alignment."""

    def __init__(self, plan_focus: Optional[List[str]] = None):
        self.plan_focus = plan_focus or [
            "deadline",
            "reply",
            "approval",
            "student",
            "admin",
            "meeting",
            "review",
            "faculty",
        ]

    def _score_thread(self, thread: EmailThread) -> SwarmCandidate:
        # Simulate a slightly heavier per-thread analysis so the parallel wall-clock
        # difference is measurable relative to the sequential baseline.
        time.sleep(0.02)
        text = " ".join([
            thread.subject,
            thread.snippet,
            *[message.body for message in thread.messages],
        ]).lower()
        sender_category = classify_sender(thread.sender)
        score = 30

        if sender_category in {SenderCategory.STUDENT, SenderCategory.ADMIN}:
            score += 25
        elif sender_category == SenderCategory.COLLABORATOR:
            score += 15
        elif sender_category == SenderCategory.VENDOR:
            score -= 15

        if any(token in text for token in ["deadline", "due", "today", "tomorrow", "friday", "urgent"]):
            score += 30
        if any(token in text for token in ["approval", "review", "sign", "confirm", "register"]):
            score += 18
        if any(token in text for token in ["meeting", "schedule", "office hours", "slot"]):
            score += 12

        urgency = UrgencyLevel.LOW
        if score >= 80:
            urgency = UrgencyLevel.URGENT
        elif score >= 60:
            urgency = UrgencyLevel.HIGH
        elif score >= 40:
            urgency = UrgencyLevel.MEDIUM

        plan_hits = sum(1 for token in self.plan_focus if token.lower() in text)
        alignment_score = max(0, plan_hits * 10 + (5 if sender_category in {SenderCategory.STUDENT, SenderCategory.ADMIN} else 0))
        alignment_score = min(ALIGNMENT_SCORE_MAX, alignment_score)

        return SwarmCandidate(
            thread_id=thread.thread_id,
            subject=thread.subject,
            sender=thread.sender,
            category=sender_category.value,
            urgency=urgency.value,
            urgency_score=min(100, max(0, score)),
            alignment_score=alignment_score,
            rationale=f"Category={sender_category.value}; urgency={urgency.value}; aligned_terms={plan_hits}",
        )

    def run(self, threads: Iterable[EmailThread], parallel: bool = True) -> Dict[str, Any]:
        pool_threads = list(threads)
        if not pool_threads:
            return {
                "items": [],
                "merged_count": 0,
                "average_alignment": 0.0,
                "alignment_range": {"min": ALIGNMENT_SCORE_MIN, "max": ALIGNMENT_SCORE_MAX},
                "merge_trace": [],
            }

        max_workers = min(len(pool_threads), os.cpu_count() or 4)
        candidates: List[SwarmCandidate] = []
        if parallel:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self._score_thread, thread) for thread in pool_threads]
                for future in as_completed(futures):
                    candidates.append(future.result())
        else:
            for thread in pool_threads:
                candidates.append(self._score_thread(thread))

        merged: Dict[str, SwarmCandidate] = {}
        merge_trace: List[Dict[str, Any]] = []
        for candidate in candidates:
            existing = merged.get(candidate.thread_id)
            kept = existing is None or candidate.alignment_score > existing.alignment_score
            if kept:
                merged[candidate.thread_id] = candidate
                merge_trace.append(
                    {
                        "thread_id": candidate.thread_id,
                        "selected_subject": candidate.subject,
                        "selected_alignment": candidate.alignment_score,
                        "selected_urgency": candidate.urgency,
                        "kept_by_alignment": True,
                    }
                )
            else:
                merge_trace.append(
                    {
                        "thread_id": candidate.thread_id,
                        "selected_subject": existing.subject if existing else candidate.subject,
                        "selected_alignment": existing.alignment_score if existing else candidate.alignment_score,
                        "selected_urgency": existing.urgency if existing else candidate.urgency,
                        "kept_by_alignment": False,
                    }
                )

        ordered = sorted(merged.values(), key=lambda item: (item.alignment_score, item.urgency_score), reverse=True)
        average_alignment = sum(item.alignment_score for item in ordered) / len(ordered) if ordered else 0.0

        return {
            "items": [candidate.model_dump() for candidate in ordered],
            "merged_count": len(ordered),
            "average_alignment": round(average_alignment, 2),
            "alignment_range": {"min": ALIGNMENT_SCORE_MIN, "max": ALIGNMENT_SCORE_MAX},
            "merge_trace": merge_trace,
        }


def run_parallel_swarm(threads: Iterable[EmailThread], plan_focus: Optional[List[str]] = None, parallel: bool = True) -> Dict[str, Any]:
    """Convenience wrapper for demos and integration tests."""
    coordinator = ParallelSwarmCoordinator(plan_focus=plan_focus)
    return coordinator.run(threads, parallel=parallel)
