"""Lab 12: Safety & Governance — Approval, Eval, Rollback.

This governance pass follows the same approval gate pattern as the dashboard's
`send_email_guarded()` flow: only the authenticated faculty mailbox owner may
approve or publish, and rollback must restore the actual prior content state.
"""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from core.models import ApprovalStatus, DraftReply


class ReleaseRecord(BaseModel):
    version: int
    status: str
    approved_by: str
    approved: bool
    content: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class GovernanceAgent:
    """Use the same underlying approval contract as the dashboard guardrail."""

    def __init__(self, mailbox_owner: str = "faculty_owner"):
        self.mailbox_owner = mailbox_owner
        self.catalog: Dict[int, ReleaseRecord] = {}
        self.latest_version = 0

    def _require_mailbox_scope(self, actor: str, mailbox_owner: str | None = None) -> None:
        owner = mailbox_owner or self.mailbox_owner
        if not actor or actor.strip() == "":
            raise PermissionError("Access denied: no authenticated actor provided.")
        if actor != owner:
            raise PermissionError(
                f"Access denied: actor '{actor}' is not the authenticated mailbox owner '{owner}'. "
                "Never expose email content beyond the faculty's own access scope."
            )

    def _require_approval_guardrail(self, draft: DraftReply, actor: str, mailbox_owner: str | None = None) -> None:
        owner = mailbox_owner or self.mailbox_owner
        if draft.status != ApprovalStatus.APPROVED:
            raise PermissionError(
                "Guardrail violation: a draft must already be approved before it can publish."
            )
        if draft.approved_by != owner:
            raise PermissionError(
                f"Guardrail violation: only the mailbox owner '{owner}' may approve a release."
            )
        self._require_mailbox_scope(actor, owner)

    def publish_release(self, draft: DraftReply, actor: str, mailbox_owner: str | None = None) -> ReleaseRecord:
        owner = mailbox_owner or self.mailbox_owner
        self._require_approval_guardrail(draft, actor, owner)

        version = self.latest_version + 1
        record = ReleaseRecord(
            version=version,
            status="published",
            approved_by=actor,
            approved=True,
            content={
                "draft_id": draft.draft_id,
                "thread_id": draft.thread_id,
                "recipient": draft.recipient,
                "subject": draft.subject,
                "body": draft.body,
                "approved_by": draft.approved_by,
            },
            metrics={
                "publish_blocked": False,
                "approval_required": True,
                "approved_by": actor,
                "item_count": 1,
                "status": "approved",
            },
        )
        self.catalog[version] = record
        self.latest_version = version
        return record

    def rollback(self, version: int, actor: str, mailbox_owner: str | None = None) -> Dict[str, Any]:
        owner = mailbox_owner or self.mailbox_owner
        self._require_mailbox_scope(actor, owner)
        if version not in self.catalog:
            return {"restored": False, "version": version, "reason": "version not found"}

        restored = self.catalog[version]
        return {
            "restored": True,
            "version": restored.version,
            "status": "rolled_back",
            "approved_by": restored.approved_by,
            "restored_content": restored.content,
            "reason": f"Rollback to version {version} restored the prior approved state.",
        }


def run_governance_check(draft: Dict[str, Any], actor: str = "faculty_owner") -> Dict[str, Any]:
    """Backward-compatible convenience wrapper used by the demo scripts."""
    agent = GovernanceAgent()
    release = agent.publish_release(
        DraftReply(
            draft_id=draft["draft_id"],
            thread_id=draft["thread_id"],
            recipient=draft["recipient"],
            subject=draft["subject"],
            body=draft["body"],
            status=ApprovalStatus(draft["status"]),
            approved_by=draft.get("approved_by", actor),
        ),
        actor=actor,
    )
    return {
        "release": release.model_dump(),
        "rollback": agent.rollback(release.version, actor=actor),
    }
