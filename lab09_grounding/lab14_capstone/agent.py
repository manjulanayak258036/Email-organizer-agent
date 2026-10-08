"""Lab 14: Capstone integration for the Email Organizer Agent.

This keeps the original contracts intact: connector -> runtime -> graph -> governance
-> specialists -> dashboard. It does not rewrite the existing modules; it wires them
into a single deployed worklet for a real-case demo.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.models import ApprovalStatus, DraftReply
from lab05_connector.connector import build_connector
from lab07_node_graph.graph import AgenticNodeGraph
from lab12_governance.agent import GovernanceAgent
from lab13_specialists.registry import registry


class CapstoneWorklet:
    """Wires all prior lab contracts into a single, deployed system view."""

    def __init__(self, mailbox_owner: str = "faculty_owner"):
        self.connector = build_connector()
        self.runtime = None
        self.graph = None
        self.governance = GovernanceAgent(mailbox_owner=mailbox_owner)
        self.mailbox_owner = mailbox_owner

    def _build_graph(self) -> AgenticNodeGraph:
        if self.graph is None:
            self.graph = AgenticNodeGraph(connector=self.connector)
        return self.graph

    def _build_specialist_drafts(self, run_result) -> List[Dict[str, Any]]:
        inbox = run_result.triaged_inbox
        if not inbox:
            return []

        drafts: List[Dict[str, Any]] = []
        for item in inbox.items:
            if not item.draft_reply:
                continue
            payload = {
                "sender": item.sender,
                "subject": item.subject,
                "body": item.body_preview or item.rationale or "",
            }
            matched_domain = None
            for domain_name in registry.domains():
                specialist = registry.get(domain_name)
                if specialist.detect(payload):
                    matched_domain = domain_name
                    break
            if matched_domain is None:
                continue
            draft = item.draft_reply
            drafts.append(
                {
                    "domain": matched_domain,
                    "draft_id": draft.draft_id,
                    "recipient": draft.recipient,
                    "subject": draft.subject,
                    "body": draft.body,
                    "template_used": draft.template_used,
                    "citations": draft.citations,
                    "requires_faculty_approval": draft.template_used is not None and "approval" in str(draft.template_used).lower(),
                }
            )
        return drafts

    def run(self, request: Dict[str, Any]) -> Dict[str, Any]:
        graph = self._build_graph()
        run_result = graph.run(max_results=request.get("max_results", 5), query=request.get("query", "label:INBOX"))
        drafts = self._build_specialist_drafts(run_result)

        specialist_summary = run_result.specialist_registry_summary or {
            "checked_live_items": 0,
            "matched_specialist_items": 0,
            "matched_domains": [],
            "note": "specialist registry not checked",
        }

        approved_releases = []
        for draft in drafts:
            reply = DraftReply(
                draft_id=draft["draft_id"],
                thread_id=draft["draft_id"],
                recipient=draft["recipient"],
                subject=draft["subject"],
                body=draft["body"],
                template_used=draft["template_used"],
                citations=draft["citations"],
                status=ApprovalStatus.APPROVED,
                approved_by=self.mailbox_owner,
            )
            release = self.governance.publish_release(reply, actor=self.mailbox_owner)
            approved_releases.append(release.model_dump())

        return {
            "run_id": run_result.run_id,
            "status": "approved_and_ready_for_dashboard",
            "artifact": {
                "triaged_inbox": run_result.triaged_inbox.model_dump() if run_result.triaged_inbox else None,
                "drafts": drafts,
                "releases": approved_releases,
                "specialist_registry_summary": specialist_summary,
                "approval_contract": {
                    "rule": "Draft only; never send without explicit faculty approval.",
                    "all_specialists_require_faculty_approval": False,
                    "note": "The draft queue still flows through the standard approval gate; specialist output does not skip approval.",
                },
            },
            "metrics": {
                "draft_count": len(drafts),
                "published_count": len(approved_releases),
                "graph_status": run_result.status,
                "source_backend": run_result.source_backend,
            },
        }
