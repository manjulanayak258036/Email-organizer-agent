"""Lab 1 Demonstration Script: Planner Loop (clarify -> plan -> revise).

Proves acceptance criteria from Chapter 3:
"Given a vague request it asks at least two clarifying questions and yields a coherent, editable plan."
"""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab01_agent_loop.planner import CoordinatorPlanner


def main():
    print("=" * 70)
    print("LAB 1: Agent vs Chatbot — The Planner Loop")
    print("=" * 70)

    planner = CoordinatorPlanner()

    # Step 1: Submit a deliberately vague user request
    vague_request = "Please organize my faculty inbox."
    print(f"\n[User Input] Vague Request: '{vague_request}'")

    is_complete, questions, initial_params = planner.clarify(vague_request)

    print(f"\n[Planner Clarification Check] Is complete: {is_complete}")
    print(f"[Planner Clarification Check] Number of clarifying questions: {len(questions)}")
    for i, q in enumerate(questions, 1):
        print(f"  Question {i}: {q}")

    # Acceptance Test 1: Must ask at least two clarifying questions
    assert not is_complete, "Acceptance Failure: Vague request should not be marked complete."
    assert len(questions) >= 2, f"Acceptance Failure: Expected >= 2 clarifying questions, got {len(questions)}."
    print("\n[ACCEPTANCE PASS] Asked at least two clarifying questions on vague request.")

    # Step 2: Simulate user answering the clarifying questions
    print("\n[User Feedback] Providing answers to clarifying questions...")
    answers = {
        "time_window": "past 48 hours",
        "urgency_focus": True,
        "draft_templates": True,
        "scope_filter": "student inquiries and faculty senate deadlines",
    }
    for k, v in answers.items():
        print(f"  Answer [{k}]: {v}")

    is_complete, questions, clarified_params = planner.clarify(vague_request, answers=answers)
    assert is_complete, "Clarification should be complete once answers are provided."
    assert len(questions) == 0

    # Step 3: Propose coherent, editable outline plan
    print("\n[Planner Action] Proposing editable outline plan...")
    plan = planner.propose_plan(clarified_params)
    print(f"Plan ID: {plan.plan_id}")
    print(f"Target Scope: {plan.target_scope}")
    print(f"Number of Steps: {len(plan.steps)}")
    for step in plan.steps:
        print(f"  Step {step.step_id}: {step.name} -> {step.description}")

    # Acceptance Test 2: Plan must be coherent and editable (not yet locked)
    assert not plan.locked, "Plan should be editable before user approval."
    assert len(plan.steps) >= 4, "Plan should outline the key stages of the email triage worklet."
    print("\n[ACCEPTANCE PASS] Yielded a coherent, editable outline plan.")

    # Step 4: User requests revision
    revision_feedback = "Please skip vendor newsletters and prioritize student project submissions."
    print(f"\n[User Feedback] Revision Request: '{revision_feedback}'")
    revised_plan = planner.revise(plan, revision_feedback)

    print("\n[Planner Action] Revised Plan Steps:")
    for step in revised_plan.steps:
        print(f"  Step {step.step_id}: {step.name} -> {step.description}")

    # Acceptance Test 3: Plan revisions reflected
    assert revised_plan.parameters.get("exclude_vendors") is True
    assert revised_plan.parameters.get("prioritize_students") is True
    print("\n[ACCEPTANCE PASS] Successfully revised plan based on feedback.")

    # Step 5: Lock plan before pipeline execution
    locked_plan = planner.lock_plan(revised_plan)
    assert locked_plan.locked is True
    print("\n[Plan Finalized] Plan locked for pipeline execution.")
    print("=" * 70)
    print("ALL LAB 1 ACCEPTANCE CRITERIA SATISFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
