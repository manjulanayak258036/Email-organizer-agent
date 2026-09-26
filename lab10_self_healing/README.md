# Lab 10: Ops Resilience - Validate, Diagnose, Fix

## Purpose

This lab models the Chapter 3 self-healing requirement:
> Validate the current output, diagnose the exact failing condition, and repair only the broken segment until the run passes or the retry budget is exhausted.

## Executive behavior

The self-healing loop:

1. runs validation against the current candidate set
2. captures precise failure reasons
3. repairs only the broken candidate(s)
4. re-runs validation until the set passes or the retry budget is reached

## Files

- `agent.py` — validation + repair loop
- `demo_lab10.py` — acceptance script and evidence output
- `README.md` — lab overview

## Run

```bash
python lab10_self_healing/demo_lab10.py
```

## Acceptance

The acceptance script proves that a failing candidate is diagnosed, regenerated from the relevant source thread, and the final output passes validation within the allowed retry budget.
