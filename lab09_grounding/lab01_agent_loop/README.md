# Lab 1: Agent vs Chatbot — The Planner Loop

## Goal
Establish the foundational agent loop (`clarify -> plan -> revise`) rather than acting like a one-shot chatbot that makes assumptions or answers without complete parameters.

## What It Adds
A coordinator planner loop that:
1. Detects underspecified or vague requests.
2. Formulates at least two targeted clarifying questions covering time scope, urgency markers, and standard response libraries.
3. Generates a coherent, editable multi-stage plan for the Email Organizer Worklet.
4. Revises the plan interactively based on user feedback before locking the plan for execution.

## Acceptance Criteria (Chapter 3 PDF)
> **Acceptance**: Given a vague request it asks at least two clarifying questions and yields a coherent, editable plan.

## How to Run the Demo
```bash
python lab01_agent_loop/demo_lab01.py
```

## Proof of Acceptance
When executed with the vague request `"Please organize my faculty inbox."`, `demo_lab01.py`:
- Emits $\ge 2$ clarifying questions.
- Ingests clarifications and produces a 6-step outline plan.
- Accepts human revisions (`"skip vendor newsletters and prioritize student project submissions"`).
- Locks the updated structured plan for Phase A/B pipeline execution.
