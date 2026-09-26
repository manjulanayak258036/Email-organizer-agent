# Lab 7: Agentic Node Graph

## Purpose

Implements the Chapter 3 "Lab 7 - Agentic Node Graph" specification:
> Wire the specialist agents into one explicit graph with state and branching.

The graph connects the Phase-A components into the required topology:

```python
graph.chain(ingest -> plan -> workers -> validate)
graph.edge(validate --fail--> workers)   # bounded retry
graph.edge(validate --pass--> assemble -> gate -> publish)
```

## Key Design

Lab 7 does **not** create a second runtime. `AgenticNodeGraph` uses
`lab06_runtime.GovernedRuntime` for execution, audit, budget, approval gates,
and checkpoints. The graph layer owns only:

- node ordering
- graph state
- validation branching
- bounded retry behavior

## Nodes

| Node | Responsibility |
|------|----------------|
| `ingest` | Read inbox, contacts, and calendar through the Lab 5 connector |
| `plan` | Produce a locked plan through the Lab 3 planning skill |
| `workers` | Classify, rank, extract actions/meetings, and draft replies |
| `validate` | Enforce draft presence, no completed actions, and no confirmed meetings |
| `assemble` | Render the triaged inbox through the Lab 3 formatting skill |
| `gate` | Route the review artifact through the Lab 6 approval gate |
| `publish` | Publish only to the mailbox-owner review queue; no email is sent |

## Pitfall Avoided

> Bound the retry edge - an unbounded regenerate loop can spin forever.

`max_retries` is explicit. The demo injects one validation failure to prove the
graph retries and recovers, then runs a forced-failure case to prove the graph
stops after the retry budget is exhausted.

## Files

| File | Description |
|------|-------------|
| `graph.py` | `AgenticNodeGraph`, graph state, validation report, and bounded retry logic |
| `demo_lab07.py` | Acceptance script with pass-after-retry and retry-exhaustion proofs |
| `README.md` | This file |

## Running

```bash
python lab07_node_graph/demo_lab07.py
```

## Acceptance

One command yields a validated triaged inbox with draft replies end to end, and
the validation failure back-edge is bounded rather than open-ended.
