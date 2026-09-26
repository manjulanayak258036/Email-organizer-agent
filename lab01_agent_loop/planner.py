"""Lab 1: Agent vs Chatbot — Coordinator Planner Loop.

Implements the clarify -> plan -> revise agent loop from Chapter 3:
- Given a vague request, identifies underspecified parameters and asks >= 2 clarifying questions.
- Proposes a coherent, editable outline plan for triaged inbox with draft replies.
- Revises plan iteratively based on user feedback until approved.
"""

from __future__ import annotations
import uuid
from typing import Dict, List, Tuple, Any, Optional
from core.models import ExecutionPlan, PlanStep


class CoordinatorPlanner:
    """The AURA Coordinator Planner loop."""

    REQUIRED_DIMENSIONS = [
        ("time_window", "What time window or date range of incoming emails should be triaged? (e.g. 'past 24 hours', 'this week')"),
        ("urgency_focus", "Should urgent emails (administrative deadlines, urgent student requests) trigger immediate high-priority flagging?"),
        ("draft_templates", "Should the draft replies automatically reuse the faculty standard response library for common queries?"),
        ("scope_filter", "Are there any specific sender categories to focus on or exclude (e.g. prioritize students, skip newsletters)?"),
    ]

    def clarify(
        self,
        user_request: str,
        answers: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Evaluates whether user request contains sufficient detail or requires clarification.

        Returns:
            is_complete: bool
            questions: List of at least two clarifying questions if incomplete
            clarified_params: Dict of resolved parameters
        """
        answers = answers or {}
        req_lower = user_request.lower()

        is_vague = len(user_request.split()) < 10 or not any(
            t in req_lower for t in ["today", "24h", "week", "yesterday", "since", "days"]
        )

        resolved_params: Dict[str, Any] = {
            "raw_request": user_request,
            "time_window": answers.get("time_window"),
            "urgency_focus": answers.get("urgency_focus"),
            "draft_templates": answers.get("draft_templates"),
            "scope_filter": answers.get("scope_filter"),
        }

        unresolved_questions = []
        for dim_key, question_text in self.REQUIRED_DIMENSIONS:
            if resolved_params.get(dim_key) is None:
                unresolved_questions.append(question_text)

        if not answers and is_vague:
            if len(unresolved_questions) < 2:
                unresolved_questions.append("Would you like meeting invites checked against your Google Calendar availability?")
            return False, unresolved_questions, resolved_params

        if unresolved_questions:
            return False, unresolved_questions, resolved_params

        return True, [], resolved_params

    def propose_plan(self, clarified_params: Dict[str, Any]) -> ExecutionPlan:
        """Proposes a coherent, editable outline plan for triaging emails and preparing draft replies."""
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        time_window = clarified_params.get("time_window", "past 24 hours")
        scope = clarified_params.get("scope_filter", "all faculty mail")

        steps = [
            PlanStep(
                step_id=1,
                name="Ingestion & Classification",
                description=f"Fetch unread email threads from {time_window} for scope [{scope}]. Tag by sender category (student, admin, collaborator, vendor, other)."
            ),
            PlanStep(
                step_id=2,
                name="Priority & Urgency Scoring",
                description="Scan emails for deadlines, escalation markers, and urgent keywords. Rank threads into priority tiers (urgent, high, medium, low)."
            ),
            PlanStep(
                step_id=3,
                name="Draft Reply Generation",
                description="Propose replies for actionable emails, matching standard response templates and citing thread history."
            ),
            PlanStep(
                step_id=4,
                name="Action-Item & Meeting Extraction",
                description="Extract commitments, tasks, and meeting requests with proposed calendar slots."
            ),
            PlanStep(
                step_id=5,
                name="Validation Gate",
                description="Execute automated acceptance checks (source grounding, rule compliance, no-auto-send enforcement)."
            ),
            PlanStep(
                step_id=6,
                name="Faculty Review & Governed Publish",
                description="Present triaged inbox and draft queue to faculty for hard approval gate before any send/archive action."
            ),
        ]

        return ExecutionPlan(
            plan_id=plan_id,
            target_scope=f"Triage {time_window} ({scope})",
            parameters=clarified_params,
            steps=steps,
            locked=False
        )

    def revise(self, plan: ExecutionPlan, user_feedback: str) -> ExecutionPlan:
        """Revises the plan based on human feedback."""
        feedback_lower = user_feedback.lower()
        new_steps = [step.model_copy() for step in plan.steps]
        new_params = dict(plan.parameters)

        if any(w in feedback_lower for w in ["skip vendor", "exclude vendor", "ignore newsletter", "vendor newsletter"]):
            new_params["exclude_vendors"] = True
            for step in new_steps:
                if step.step_id == 1:
                    step.description += " [FILTER: Auto-archive vendor newsletters]"

        if "student" in feedback_lower and any(w in feedback_lower for w in ["priorit", "urgent", "first"]):
            new_params["prioritize_students"] = True
            for step in new_steps:
                if step.step_id == 2:
                    step.description += " [RULE: Boost student queries to HIGH/URGENT tier]"

        if any(w in feedback_lower for w in ["calendar", "meeting", "slot", "schedule"]):
            new_params["sync_calendar"] = True
            for step in new_steps:
                if step.step_id == 4:
                    step.description += " [CALENDAR: Check conflicting events on faculty Google Calendar]"

        revisions = new_params.setdefault("revisions", [])
        revisions.append(user_feedback)

        return ExecutionPlan(
            plan_id=plan.plan_id,
            target_scope=plan.target_scope,
            parameters=new_params,
            steps=new_steps,
            locked=False
        )

    def lock_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Locks the plan before pipeline execution begins (per Section 3.7)."""
        plan.locked = True
        return plan
