# Lab 9: Deep Research - Ground & Evidence

## Purpose

Implements the Chapter 3 "Lab 9 - Deep Research" requirement:
> Every candidate output must be grounded in a real in-scope source and carry an evidence record; ungrounded candidates must be rejected.

## Design

The grounding layer checks candidate content against:

- the real email thread history
- past reply patterns / owner history

If the candidate is not backed by one of those in-scope sources, it is rejected rather than published.

## Files

| File | Description |
|------|-------------|
| `agent.py` | `GroundingAgent` and evidence record model |
| `demo_lab09.py` | Acceptance script proving grounded candidates survive and ungrounded candidates are rejected |
| `README.md` | This file |

## Running

```bash
python lab09_grounding/demo_lab09.py
```

## Acceptance

Every output must map to an in-scope source; the acceptance script proves the grounded path passes and the ungrounded path is blocked.
