"""Lab 12 acceptance script: real rollback + access control + approval gate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import ApprovalStatus, DraftReply
from lab12_governance.agent import GovernanceAgent


def main() -> None:
    print("=" * 80)
    print("LAB 12: Safety & Governance - Approval, Eval, Rollback")
    print("=" * 80)
    print("Command to run: python lab12_governance/demo_lab12.py")

    owner = "faculty_owner"
    agent = GovernanceAgent(mailbox_owner=owner)

    v1 = DraftReply(
        draft_id="draft_v1",
        thread_id="thread_001",
        recipient="student@university.edu",
        subject="Follow-up on thesis committee form",
        body="Version A: I have reviewed the thesis committee form and confirm it is ready for submission.",
        status=ApprovalStatus.APPROVED,
        approved_by=owner,
    )
    v2 = DraftReply(
        draft_id="draft_v2",
        thread_id="thread_001",
        recipient="student@university.edu",
        subject="Follow-up on thesis committee form",
        body="Version B: I have reviewed the thesis committee form and am asking for a revised submission before approval.",
        status=ApprovalStatus.APPROVED,
        approved_by=owner,
    )

    print("\n-- VERSION 1 PUBLISH (CONTENT A) --")
    release_v1 = agent.publish_release(v1, actor=owner)
    print(release_v1.model_dump())
    print(f"Published version 1 body == A: {release_v1.content['body'] == v1.body}")

    print("\n-- VERSION 2 PUBLISH (CONTENT B) --")
    release_v2 = agent.publish_release(v2, actor=owner)
    print(release_v2.model_dump())
    print(f"Published version 2 body == B: {release_v2.content['body'] == v2.body}")

    print("\n-- ROLLBACK TO VERSION 1 --")
    rollback = agent.rollback(version=1, actor=owner)
    print(rollback)
    print(f"Rollback restored content A: {rollback['restored_content']['body'] == v1.body}")
    print(f"Rollback did not restore version B: {rollback['restored_content']['body'] != v2.body}")

    assert release_v1.content["body"] == v1.body
    assert release_v2.content["body"] == v2.body
    assert rollback["restored"] is True
    assert rollback["restored_content"]["body"] == v1.body
    assert rollback["restored_content"]["body"] != v2.body

    print("\n-- ACCESS CONTROL CHECK --")
    unauthorized_actor = "admin_staff"
    try:
        agent.publish_release(v2, actor=unauthorized_actor)
        raise AssertionError("Unauthorized publish unexpectedly succeeded.")
    except PermissionError as exc:
        print(f"Unauthorized publish blocked: {exc}")

    try:
        agent.rollback(version=1, actor=unauthorized_actor)
        raise AssertionError("Unauthorized rollback unexpectedly succeeded.")
    except PermissionError as exc:
        print(f"Unauthorized rollback blocked: {exc}")

    print("\n[ACCEPTANCE PASS] The rollback restores the actual previous approved state (A), and access control blocks unauthorized actors from publishing or rolling back.")


if __name__ == "__main__":
    main()
