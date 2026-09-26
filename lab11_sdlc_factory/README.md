# Lab 11: SDLC Factory - Spec → Tested Output

## Purpose

This lab turns the locked plan into a tested build pipeline. The acceptance suite is a hard gate: no triaged inbox with draft replies advances to the mailbox owner without a green report.

## Behavior

1. Build the artifact from the locked plan.
2. Validate the artifact against the acceptance suite.
3. Only allow the result into the human review gate when the report passes.

## Files

- `agent.py` — factory build + acceptance validation
- `demo_lab11.py` — end-to-end acceptance script
- `README.md` — overview

## Run

```bash
python lab11_sdlc_factory/demo_lab11.py
```

## Acceptance

The script confirms that the build is blocked until a passing acceptance report exists, and that passing artifacts carry complete evidence-backed draft records.
