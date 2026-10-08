# Lab 6: Governed Runtime

## Purpose

Implements the Chapter 3 "Lab 6 - Governed Runtime" specification:
> Every agent step runs inside a governed runtime that logs inputs and outputs,
> enforces budgets and approval gates, and checkpoints before advancing so a
> crashed run can resume from its last safe point.

## Key Design

```python
runtime.register(plan_node, tool_node, skill_node, memory_node, connector_node)
for step in plan:
    result = runtime.run(step)
    if result.needs_approval:
        runtime.gate(step)
    runtime.checkpoint(step.id, result)
```

The runtime wraps the Phase-A components already built in Labs 1-5:

- `PlanNode`: Lab 3 `PlanningSkill`
- `ToolNode`: Lab 2 typed tools and domain calculator
- `SkillNode`: Lab 3 `FormattingSkill`
- `MemoryNode`: Lab 4 long-term memory retrieval
- `ConnectorNode`: Lab 5 `MCPStyleConnector`

## Pitfall Avoided

> Losing work after a crash because the pipeline advanced before checkpointing.

`GovernedRuntime.run()` writes durable checkpoints before the next step can
advance. A second runtime with the same `run_id` loads completed steps and skips
re-execution.

## Governance Features

- JSONL audit trail for every registered node and executed step.
- Input and output summaries recorded for each action.
- Per-step and total budget enforcement.
- Human approval gate abstraction, simulated with auto-approval in the demo.
- Durable checkpoint store for crash recovery.

## Files

| File | Description |
|------|-------------|
| `runtime.py` | `GovernedRuntime`, `RuntimeNode`, `StepResult`, checkpointing, approval gate, and budget tracking |
| `demo_lab06.py` | Acceptance script verifying audit, budget, approval, checkpoint, and resume behavior |
| `__init__.py` | Package exports |

## Running

```bash
python lab06_runtime/demo_lab06.py
```

The demo uses a temporary scratch directory for audit and checkpoint files so
repeat runs do not collide with prior verification output.

## Acceptance Results

| Step | Check | Result |
|------|-------|--------|
| 1 | Register all runtime nodes | PASS |
| 2 | Execute all five wrapped lab components | PASS |
| 3 | Audit every step with inputs and outputs | PASS |
| 4 | Checkpoint every completed step | PASS |
| 5 | Resume with same `run_id` skips completed work | PASS |
| 6 | Reject over-budget execution | PASS |
| 7 | Route approval-required node through approval gate | PASS |
