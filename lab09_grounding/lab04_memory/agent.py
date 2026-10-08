"""Lab 4: Retrieval Agent — Foundations of Later Screening.

Implements the Chapter 3 Lab 4 retrieval node:
- Uses MemoryManager to maintain strict separation of session state vs long-term storage.
- Given an email candidate, executes the memory split:
    state.draft = candidate
    hits = memory.retrieve('store', tags)
    prior = memory.retrieve('history', memory.embed(candidate), k=k)
- Synthesizes grounded evidence records without contaminating the baseline archive.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from core.models import EmailThread, DraftReply, ApprovalStatus
from lab04_memory.memory import (
    MemoryManager,
    SessionState,
    StoreItem,
    HistoryItem,
)


class RetrievalResult(BaseModel):
    """Encapsulates the output of a retrieval cycle for a given email task."""
    thread_id: str
    active_draft: DraftReply
    store_hits: List[StoreItem]
    prior_history_hits: List[Dict[str, Any]]
    best_matching_prior: Optional[Dict[str, Any]] = None
    grounding_citations: List[str] = Field(default_factory=list)


class RetrievalAgent:
    """Retrieval Agent activating the Retrieval Node for the Email Organizer Worklet."""

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        self.memory = memory_manager or MemoryManager()

    def process_email_candidate(
        self,
        thread: EmailThread,
        retrieval_tags: List[str],
        candidate_template: str = "standard_acknowledgement",
        k_priors: int = 3
    ) -> RetrievalResult:
        """Executes the exact Lab 4 memory split and grounding retrieval workflow."""
        # Step 1: Create candidate draft and place in SHORT-TERM session state
        candidate = DraftReply(
            draft_id=f"draft_{thread.thread_id}",
            thread_id=thread.thread_id,
            recipient=thread.sender,
            subject=f"Re: {thread.subject}",
            body=f"Candidate draft response for thread {thread.thread_id}.",
            template_used=candidate_template,
            citations=[f"Thread {thread.thread_id}"],
            status=ApprovalStatus.DRAFT,
            approved_by=None
        )

        # Lab 4 Pseudocode line 1: state.draft = candidate (short-term)
        self.memory.state.set_draft(candidate)

        # Step 2: Long-term reference store retrieval by tags
        # Lab 4 Pseudocode line 2: hits = retrieve(store, tags)
        hits: List[StoreItem] = self.memory.retrieve("store", tags=retrieval_tags)

        # Step 3: Historical archive retrieval by embedding similarity
        # Lab 4 Pseudocode line 3: prior = retrieve(history, embed(candidate), k=5)
        candidate_embedding = self.memory.embed(thread)
        raw_priors: List[Tuple[HistoryItem, float]] = self.memory.retrieve(
            "history",
            query=candidate_embedding,
            k=k_priors
        )

        # Step 4: Package serializable prior hits with similarity metrics
        prior_hits: List[Dict[str, Any]] = []
        for item, score in raw_priors:
            prior_hits.append({
                "history_id": item.history_id,
                "thread_id": item.thread_id,
                "subject": item.subject,
                "similarity_score": round(score, 4),
                "prior_faculty_reply": item.faculty_reply,
                "category": item.category,
                "tags": item.tags
            })

        best_prior = prior_hits[0] if prior_hits else None

        # Build citations linking store policies and past faculty replies
        citations = [f"Direct Email Thread: {thread.thread_id} ({thread.subject})"]
        for h in hits:
            citations.append(f"Store Policy: {h.title} (tags: {h.tags})")
        if best_prior and best_prior["similarity_score"] > 0.15:
            citations.append(
                f"Historical Thread: {best_prior['thread_id']} (similarity: {best_prior['similarity_score']:.2f})"
            )

        # Enrich the candidate draft with grounded citations and prior context
        self.memory.state.draft.citations = citations
        if best_prior and best_prior.get("prior_faculty_reply"):
            self.memory.state.draft.evidence_record = {
                "matched_policy": hits[0].title if hits else None,
                "top_similar_prior_id": best_prior["thread_id"],
                "similarity_score": best_prior["similarity_score"],
                "reference_reply_snippet": best_prior["prior_faculty_reply"][:120] + "..."
            }

        return RetrievalResult(
            thread_id=thread.thread_id,
            active_draft=self.memory.state.draft,
            store_hits=hits,
            prior_history_hits=prior_hits,
            best_matching_prior=best_prior,
            grounding_citations=citations
        )

    def verify_memory_partition(self, initial_store_count: int, initial_history_count: int) -> bool:
        """Verifies that mutating short-term session state has zero side-effects on long-term stores."""
        # Mutate short-term draft aggressively
        if self.memory.state.draft:
            self.memory.state.draft.body = "OVERWRITTEN_IN_SESSION_STATE_DRAFT"
            self.memory.state.draft.status = ApprovalStatus.PENDING_REVIEW

        # Confirm long-term reference store items remain unchanged
        store_intact = (len(self.memory.long_term.store) == initial_store_count)
        history_intact = (len(self.memory.long_term.history) == initial_history_count)

        # Confirm no store item was overwritten with session draft content
        no_leakage = not any("OVERWRITTEN_IN_SESSION_STATE_DRAFT" in s.content for s in self.memory.long_term.store)
        no_history_leak = not any(
            h.faculty_reply and "OVERWRITTEN_IN_SESSION_STATE_DRAFT" in h.faculty_reply
            for h in self.memory.long_term.history
        )

        return store_intact and history_intact and no_leakage and no_history_leak
