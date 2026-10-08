# Lab 12: Safety & Governance - Approval, Eval, Rollback

## Purpose

This lab enforces the Chapter 3 governance requirements:

- only mailbox-owner-approved drafts may publish
- metrics are captured for release status
- a rollback path exists for prior versions

## Files

- `agent.py` — governance and rollback logic
- `demo_lab12.py` — acceptance script with approved and blocked publish cases
- `README.md` — overview

## Run

```bash
python lab12_governance/demo_lab12.py
```

## Acceptance

The demo proves that an approved draft is published and an unapproved draft remains blocked from publishing; rollback is available for a published release.
