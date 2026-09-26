"""Lab 9: Deep Research - Ground & Evidence.

The grounding agent accepts candidate outputs and checks whether each candidate is
backed by an in-scope source: the actual thread history and the owner's prior
reply patterns. This mirrors the Chapter 3 requirement that ungrounded outputs be
rejected instead of silently published.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    candidate_id: str
    status: str
    source: str = "n/a"
    source_id: str = "none"
    scope: str = "out_of_scope"
    tags: List[str] = Field(default_factory=list)
    grounding_text: str = ""
    explanation: str = ""
    in_scope: bool = False


class GroundingReport(BaseModel):
    grounded: List[str] = Field(default_factory=list)
    rejected: List[str] = Field(default_factory=list)
    evidence_table: List[Dict[str, Any]] = Field(default_factory=list)


class GroundingAgent:
    """Ground each candidate against real in-scope sources."""

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().split())

    @staticmethod
    def _keywords(text: str) -> set[str]:
        normalized = GroundingAgent._normalize(text)
        return {token for token in normalized.replace("-", " ").split() if token and len(token) > 3}

    @staticmethod
    def _infer_tags(candidate_text: str, source_text: str) -> List[str]:
        candidate_keywords = sorted(GroundingAgent._keywords(candidate_text), key=len, reverse=True)
        source_keywords = GroundingAgent._keywords(source_text)
        overlap = [kw for kw in candidate_keywords if kw in source_keywords][:5]
        if overlap:
            return overlap
        if not candidate_keywords:
            return ["general"]
        return candidate_keywords[:5]

    def _build_sources(self, threads: Iterable[Any], prior_replies: Optional[List[str]] = None) -> List[tuple[str, str, str]]:
        sources: List[tuple[str, str, str]] = []
        for thread in threads:
            text = "\n".join([
                thread.subject,
                thread.snippet,
                *[message.body for message in getattr(thread, "messages", [])],
            ])
            sources.append(("thread", thread.thread_id, text))
        for idx, reply in enumerate(prior_replies or []):
            sources.append(("prior_reply", f"prior_reply_{idx}", reply))
        return sources

    def ground_candidate(self, candidate_id: str, candidate_text: str, threads: Iterable[Any], prior_replies: Optional[List[str]] = None) -> EvidenceRecord:
        candidate_norm = self._normalize(candidate_text)
        candidate_keywords = self._keywords(candidate_text)
        sources = self._build_sources(threads, prior_replies)
        best_overlap: Optional[set[str]] = None
        best_source: Optional[tuple[str, str, str]] = None
        best_score = 0.0

        for source_type, source_id, source_text in sources:
            haystack = self._normalize(source_text)
            source_keywords = self._keywords(source_text)
            overlap = candidate_keywords & source_keywords
            score = len(overlap) / max(1, len(candidate_keywords)) if candidate_keywords else 0.0

            if score > best_score:
                best_score = score
                best_overlap = overlap
                best_source = (source_type, source_id, source_text)

            if candidate_norm in haystack or candidate_text in source_text:
                explained_text = self._extract_matching_text(candidate_text, source_text)
                tags = self._infer_tags(candidate_text, source_text)
                return EvidenceRecord(
                    candidate_id=candidate_id,
                    status="grounded",
                    source=source_type,
                    source_id=source_id,
                    scope="in_scope",
                    tags=tags,
                    grounding_text=explained_text,
                    explanation=f"Matched exact wording in {source_type} {source_id}; the claim is supported by the source text.",
                    in_scope=True,
                )

            if candidate_keywords and overlap and score >= 0.35:
                explained_text = self._extract_matching_text(candidate_text, source_text)
                tags = self._infer_tags(candidate_text, source_text)
                return EvidenceRecord(
                    candidate_id=candidate_id,
                    status="grounded",
                    source=source_type,
                    source_id=source_id,
                    scope="in_scope",
                    tags=tags,
                    grounding_text=explained_text,
                    explanation=f"Found strong keyword overlap in {source_type} {source_id}; threshold satisfied for a grounded claim.",
                    in_scope=True,
                )

        if best_source is not None and best_overlap is not None:
            overlap_list = sorted(best_overlap)
            return EvidenceRecord(
                candidate_id=candidate_id,
                status="rejected",
                source=best_source[0],
                source_id=best_source[1],
                scope="out_of_scope",
                tags=self._infer_tags(candidate_text, best_source[2]),
                grounding_text="",
                explanation=f"No in-scope source matched closely enough; strongest overlap was {overlap_list} ({best_score:.0%}) but this was below the grounding threshold.",
                in_scope=False,
            )

        return EvidenceRecord(
            candidate_id=candidate_id,
            status="rejected",
            source="none",
            source_id="none",
            scope="out_of_scope",
            tags=[],
            grounding_text="",
            explanation="No in-scope thread or prior-reply source contained the claim; the item was rejected as ungrounded.",
            in_scope=False,
        )

    @staticmethod
    def _extract_matching_text(candidate: str, source_text: str) -> str:
        candidate_lower = candidate.lower()
        source_lower = source_text.lower()

        if candidate_lower in source_lower:
            start = source_lower.find(candidate_lower)
            return source_text[start:start + len(candidate)].strip()

        candidate_norm = GroundingAgent._normalize(candidate)
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", source_text):
            sentence_norm = GroundingAgent._normalize(sentence)
            if not sentence_norm:
                continue
            if candidate_norm in sentence_norm or len(set(GroundingAgent._keywords(candidate)) & set(GroundingAgent._keywords(sentence))) >= 2:
                return sentence.strip()
        return source_text[:220].strip()

    def ground_candidates(self, candidates: List[Dict[str, str]], threads: Iterable[Any], prior_replies: Optional[List[str]] = None) -> GroundingReport:
        grounded: List[str] = []
        rejected: List[str] = []
        evidence_table: List[Dict[str, Any]] = []

        for candidate in candidates:
            record = self.ground_candidate(
                candidate_id=candidate["id"],
                candidate_text=candidate["content"],
                threads=threads,
                prior_replies=prior_replies,
            )
            evidence_table.append(record.model_dump())
            if record.in_scope:
                grounded.append(candidate["id"])
            else:
                rejected.append(candidate["id"])

        return GroundingReport(grounded=grounded, rejected=rejected, evidence_table=evidence_table)


def run_grounding_check(threads: Iterable[Any], candidates: List[Dict[str, str]], prior_replies: Optional[List[str]] = None) -> GroundingReport:
    """Convenience wrapper for demos and tests."""
    return GroundingAgent().ground_candidates(candidates, threads, prior_replies=prior_replies)
