# Lab 8: Parallel Swarm

## Purpose

Implements the Chapter 3 "Lab 8 - Parallel Swarm" requirement:
> Split the per-thread work across many agents in parallel, then merge the outputs by plan alignment and retain the strongest candidate for each task.

## Design

The swarm coordinator does the following:

1. Defines a shared execution plan and focus keywords.
2. Processes every thread in a worker pool.
3. Scores each thread for urgency, sender importance, and plan relevance.
4. Merges the results by thread ID and keeps the best-aligned candidate.

This follows the Chapter 3 pattern where many email threads are processed concurrently and the strongest aligned result wins.

## Files

| File | Description |
|------|-------------|
| `agent.py` | `ParallelSwarmCoordinator` and parallel merge logic |
| `demo_lab08.py` | Acceptance script proving the swarm processes and merges thread candidates |
| `README.md` | This file |

## Running

```bash
python lab08_parallel_swarm/demo_lab08.py
```

## Acceptance

The demo must process all sample inbox threads, merge them by plan alignment, and retain one best candidate per thread without duplicates.
