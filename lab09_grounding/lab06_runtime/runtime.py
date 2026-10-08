"""Lab 6: Governed Runtime — Skills, Tools, Memory, Audit.

Implements the Chapter 3 Lab 6 specification:
  "Wrap every lab component (planner, tools, skills, memory, connector) inside
   a governed runtime that enforces budgets, routes approval gates, and writes
   a full audit log of every step's inputs and outputs so a crashed run can
   resume from its last checkpoint."

Runtime pseudocode (Chapter 3):
    runtime.register(plan_node, tool_node, skill_node, memory_node, connector_node)
    for step in plan:
        result = runtime.run(step)          # executes, audits input+output
        if result.needs_approval:
            runtime.gate(step)              # blocks until approved
    runtime.checkpoint(step.id, result)     # durable snapshot after each step

Pitfall avoided: running past a failed step without checkpointing means losing
all work on crash — the runtime must write the checkpoint BEFORE advancing.
"""

from __future__ import annotations

import json
import uuid
import datetime
import copy
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from core.audit import AuditLogger
from core.models import ApprovalStatus


# =====================================================================
# 1. STEP RESULT
# =====================================================================

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_APPROVAL = "needs_approval"
    APPROVED = "approved"
    SKIPPED = "skipped"
    COMPLETED = "completed"
    FAILED = "failed"


class StepResult(BaseModel):
    step_id: str
    step_name: str
    status: StepStatus = StepStatus.PENDING
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    needs_approval: bool = False
    approval_status: Optional[str] = None
    approved_by: Optional[str] = None
    budget_used: float = 0.0
    elapsed_ms: float = 0.0
    error: Optional[str] = None
    executed_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )


# =====================================================================
# 2. RUNTIME NODE (registered callable)
# =====================================================================

class RuntimeNode(BaseModel):
    """A callable step registered with the runtime."""
    node_id: str
    name: str
    requires_approval: bool = False
    budget_limit: float = float("inf")  # arbitrary cost units

    # fn is excluded from Pydantic serialisation
    model_config = {"arbitrary_types_allowed": True}

    fn: Optional[Callable[..., Any]] = Field(default=None, exclude=True)


# =====================================================================
# 3. CHECKPOINT STORE
# =====================================================================

class CheckpointStore:
    """Durable JSON-lines checkpoint store.

    Pitfall: checkpoint is written BEFORE advancing to the next step.
    This guarantees a crashed run can always resume from the last safe point.
    """

    def __init__(self, checkpoint_path: str = "runtime_checkpoint.jsonl"):
        self.path = Path(checkpoint_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, run_id: str, step_result: StepResult) -> None:
        """Persist a completed step result. Called BEFORE advancing."""
        entry = {
            "run_id": run_id,
            "checkpointed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "step": step_result.model_dump(),
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def load_completed(self, run_id: str) -> Dict[str, StepResult]:
        """Load all successfully completed step results for a given run_id.
        Returns mapping of step_id -> StepResult for resume logic.
        """
        if not self.path.exists():
            return {}
        completed: Dict[str, StepResult] = {}
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("run_id") == run_id:
                        sr = StepResult(**entry["step"])
                        if sr.status == StepStatus.COMPLETED:
                            completed[sr.step_id] = sr
                except Exception:
                    pass
        return completed

    def list_runs(self) -> List[str]:
        """Return distinct run_ids found in the checkpoint file."""
        if not self.path.exists():
            return []
        ids = set()
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ids.add(entry["run_id"])
                except Exception:
                    pass
        return list(ids)


# =====================================================================
# 4. APPROVAL GATE
# =====================================================================

class ApprovalGate:
    """Blocks step execution until an approval decision is recorded.

    In the demo we simulate approval; in production this would surface a
    human-in-the-loop UI notification and wait for the faculty response.
    """

    def __init__(self, audit: AuditLogger):
        self._audit = audit

    def gate(
        self,
        step_result: StepResult,
        auto_approve: bool = False,
        approver: str = "faculty",
    ) -> StepResult:
        """Apply the approval gate to a step_result that needs_approval."""
        if not step_result.needs_approval:
            return step_result

        if auto_approve:
            step_result.approval_status = ApprovalStatus.APPROVED
            step_result.approved_by = approver
            step_result.status = StepStatus.APPROVED
            self._audit.log(
                agent="ApprovalGate",
                intent="approve_step",
                action=f"auto_approved:{step_result.step_id}",
                input_data={"step_id": step_result.step_id, "approver": approver},
                result={"approval_status": ApprovalStatus.APPROVED},
            )
        else:
            # Simulate blocking gate: would wait for human input
            step_result.approval_status = ApprovalStatus.PENDING_REVIEW
            self._audit.log(
                agent="ApprovalGate",
                intent="gate_step",
                action=f"pending_approval:{step_result.step_id}",
                input_data={"step_id": step_result.step_id},
                result={"status": "awaiting_human_decision"},
            )
        return step_result


# =====================================================================
# 5. BUDGET TRACKER
# =====================================================================

class BudgetTracker:
    """Tracks per-node and total budget consumption."""

    def __init__(self, total_budget: float = 100.0):
        self.total_budget = total_budget
        self._used: float = 0.0
        self._per_node: Dict[str, float] = {}

    def charge(self, node_id: str, cost: float) -> None:
        self._used += cost
        self._per_node[node_id] = self._per_node.get(node_id, 0.0) + cost

    def within_budget(self, node_id: str, node_limit: float, cost: float) -> bool:
        return (self._used + cost <= self.total_budget) and (
            self._per_node.get(node_id, 0.0) + cost <= node_limit
        )

    @property
    def used(self) -> float:
        return round(self._used, 4)

    @property
    def remaining(self) -> float:
        return round(self.total_budget - self._used, 4)

    def summary(self) -> Dict[str, Any]:
        return {
            "total_budget": self.total_budget,
            "used": self.used,
            "remaining": self.remaining,
            "per_node": {k: round(v, 4) for k, v in self._per_node.items()},
        }


# =====================================================================
# 6. THE GOVERNED RUNTIME
# =====================================================================

class GovernedRuntime:
    """Governed Runtime — wraps every lab component with audit, budget, and checkpoint.

    Chapter 3 pseudocode:
        runtime.register(plan_node, tool_node, skill_node, memory_node, connector_node)
        for step in plan:
            result = runtime.run(step)
            if result.needs_approval:
                runtime.gate(step)
            runtime.checkpoint(step.id, result)   # BEFORE advancing
    """

    def __init__(
        self,
        run_id: Optional[str] = None,
        audit_path: str = "audit_log.jsonl",
        checkpoint_path: str = "runtime_checkpoint.jsonl",
        total_budget: float = 100.0,
        auto_approve: bool = False,
        approver: str = "faculty",
    ):
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self._nodes: Dict[str, RuntimeNode] = {}
        self._audit = AuditLogger(log_path=audit_path)
        self._checkpoint = CheckpointStore(checkpoint_path=checkpoint_path)
        self._budget = BudgetTracker(total_budget=total_budget)
        self._gate = ApprovalGate(audit=self._audit)
        self._auto_approve = auto_approve
        self._approver = approver
        self._step_results: List[StepResult] = []

        self._audit.log(
            agent="GovernedRuntime",
            intent="runtime_init",
            action="initialise",
            input_data={"run_id": self.run_id, "total_budget": total_budget},
            result={"status": "ready"},
        )

    # ------------------------------------------------------------------
    # runtime.register()
    # ------------------------------------------------------------------

    def register(self, *nodes: RuntimeNode) -> None:
        """Register one or more RuntimeNodes — exact Chapter 3 pseudocode call."""
        for node in nodes:
            self._nodes[node.node_id] = node
            self._audit.log(
                agent="GovernedRuntime",
                intent="register_node",
                action=f"register:{node.name}",
                input_data={"node_id": node.node_id, "name": node.name,
                            "requires_approval": node.requires_approval,
                            "budget_limit": node.budget_limit},
                result={"registered_nodes": list(self._nodes.keys())},
            )

    # ------------------------------------------------------------------
    # runtime.run()
    # ------------------------------------------------------------------

    def run(
        self,
        step: RuntimeNode,
        inputs: Optional[Dict[str, Any]] = None,
        cost: float = 1.0,
        resume_completed: Optional[Dict[str, StepResult]] = None,
    ) -> StepResult:
        """Execute a step, audit inputs+outputs, enforce budget, gate if needed,
        checkpoint BEFORE advancing — per Chapter 3 pseudocode.

        If resume_completed contains a completed result for step.node_id, the
        step is skipped (checkpoint resume).
        """
        inputs = inputs or {}
        step_id = step.node_id

        # --- RESUME: skip already-completed steps ---
        if resume_completed and step_id in resume_completed:
            skipped = resume_completed[step_id]
            skipped_copy = skipped.model_copy()
            skipped_copy.status = StepStatus.SKIPPED
            print(f"    [RESUME] Skipping completed step '{step.name}' (loaded from checkpoint)")
            self._step_results.append(skipped_copy)
            return skipped_copy

        # --- BUDGET CHECK ---
        if not self._budget.within_budget(step_id, step.budget_limit, cost):
            sr = StepResult(
                step_id=step_id,
                step_name=step.name,
                status=StepStatus.FAILED,
                inputs=self._sanitise(inputs),
                error=f"Budget exceeded: total_used={self._budget.used}, "
                      f"node_limit={step.budget_limit}, requested={cost}",
            )
            self._audit.log(
                agent="GovernedRuntime",
                intent="budget_check",
                action=f"budget_exceeded:{step.name}",
                input_data=inputs,
                result={"error": sr.error},
                guardrail_passed=False,
            )
            self._step_results.append(sr)
            return sr

        # --- EXECUTE ---
        t_start = datetime.datetime.now(datetime.timezone.utc)
        sr = StepResult(
            step_id=step_id,
            step_name=step.name,
            status=StepStatus.RUNNING,
            inputs=self._sanitise(inputs),
            budget_used=cost,
        )

        try:
            if step.fn is not None:
                raw_output = step.fn(**inputs)
            else:
                raw_output = {"note": f"No fn registered for node '{step.name}'"}

            t_end = datetime.datetime.now(datetime.timezone.utc)
            elapsed_ms = (t_end - t_start).total_seconds() * 1000

            sr.outputs = self._sanitise(raw_output)
            sr.elapsed_ms = round(elapsed_ms, 2)
            sr.needs_approval = step.requires_approval
            sr.status = StepStatus.NEEDS_APPROVAL if step.requires_approval else StepStatus.COMPLETED

            self._budget.charge(step_id, cost)

        except Exception as exc:
            t_end = datetime.datetime.now(datetime.timezone.utc)
            sr.elapsed_ms = round((t_end - t_start).total_seconds() * 1000, 2)
            sr.status = StepStatus.FAILED
            sr.error = str(exc)

        # --- AUDIT inputs + outputs ---
        self._audit.log(
            agent="GovernedRuntime",
            intent=f"run_step:{step.name}",
            action="execute",
            input_data=sr.inputs,
            result={
                "status": sr.status,
                "outputs": sr.outputs,
                "elapsed_ms": sr.elapsed_ms,
                "error": sr.error,
            },
            guardrail_passed=(sr.status != StepStatus.FAILED),
        )

        # --- APPROVAL GATE (if needed) ---
        if sr.needs_approval and sr.status == StepStatus.NEEDS_APPROVAL:
            sr = self._gate.gate(sr, auto_approve=self._auto_approve, approver=self._approver)
            if sr.approval_status == ApprovalStatus.APPROVED:
                sr.status = StepStatus.COMPLETED

        # --- CHECKPOINT — written BEFORE advancing (pitfall avoidance) ---
        if sr.status in (StepStatus.COMPLETED, StepStatus.APPROVED):
            self.checkpoint(step_id=step_id, result=sr)

        self._step_results.append(sr)
        return sr

    # ------------------------------------------------------------------
    # runtime.gate()
    # ------------------------------------------------------------------

    def gate(self, step: RuntimeNode, step_result: StepResult) -> StepResult:
        """Explicit gate call matching Chapter 3 pseudocode interface."""
        return self._gate.gate(step_result, auto_approve=self._auto_approve, approver=self._approver)

    # ------------------------------------------------------------------
    # runtime.checkpoint()
    # ------------------------------------------------------------------

    def checkpoint(self, step_id: str, result: StepResult) -> None:
        """Persist checkpoint for step_id. Pitfall: must be called BEFORE advancing."""
        self._checkpoint.save(run_id=self.run_id, step_result=result)
        self._audit.log(
            agent="GovernedRuntime",
            intent="checkpoint",
            action=f"checkpoint:{step_id}",
            input_data={"run_id": self.run_id, "step_id": step_id},
            result={"status": result.status},
        )

    # ------------------------------------------------------------------
    # Resume support
    # ------------------------------------------------------------------

    def load_checkpoint(self) -> Dict[str, StepResult]:
        """Load all previously completed steps for this run_id (for resume)."""
        return self._checkpoint.load_completed(self.run_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def budget_summary(self) -> Dict[str, Any]:
        return self._budget.summary()

    def step_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "step_id": sr.step_id,
                "step_name": sr.step_name,
                "status": sr.status,
                "elapsed_ms": sr.elapsed_ms,
                "budget_used": sr.budget_used,
                "needs_approval": sr.needs_approval,
                "approval_status": sr.approval_status,
                "error": sr.error,
            }
            for sr in self._step_results
        ]

    def _sanitise(self, data: Any, depth: int = 0) -> Any:
        """Recursively convert data to JSON-safe primitives for audit/checkpoint storage."""
        if depth > 4:
            return str(data)[:100]
        if data is None or isinstance(data, (bool, int, float, str)):
            return data
        if isinstance(data, dict):
            return {str(k): self._sanitise(v, depth + 1) for k, v in list(data.items())[:20]}
        if isinstance(data, (list, tuple)):
            return [self._sanitise(x, depth + 1) for x in list(data)[:20]]
        if hasattr(data, "model_dump"):
            return self._sanitise(data.model_dump(), depth + 1)
        return str(data)[:200]
