# Lab 3: Skill Creation — Reusable Plan & Format Skills

## Goal
Package repeatable agent capabilities as reusable, schema-typed skills (`PlanningSkill` and `FormattingSkill`), activating the **Plan Node** and **Assembly Node** from the Chapter 3 Architecture.

## What It Adds
1. **`PlanningSkill`**:
   - Implements the exact pseudocode signature from Chapter 3:
     ```python
     skill plan(inputs) -> Plan: return expand(inputs).lock()
     ```
   - Ingests `PlanSkillInput` (typed Pydantic schema with case name, time window, scope filter, priority categories, and template preferences).
   - Generates an expanded 6-stage structured plan and locks it (`locked=True`) before pipeline execution.
2. **`FormattingSkill`**:
   - Implements the exact pseudocode signature:
     ```python
     skill format_triaged(result, template) -> Document
     ```
   - Ingests `TriagedInbox` and `TemplateSpec` (typed configuration for formats: Markdown, HTML, Plain Text).
   - Dynamically renders the 4 panels of the **Section 3.9 Dashboard Template**:
     - **Panel 1: Triaged Inbox**: Emails ranked by sender category and urgency scores.
     - **Panel 2: Draft-Reply Queue**: Proposed replies awaiting faculty sign-off, with thread citations and standard template tags.
     - **Panel 3: Action-Item List**: Detected tasks, deadlines, and commitments with `confirmed=False` hard guardrail.
     - **Panel 4: Follow-up Digest**: "Reply later" items resurfacing on schedule, plus scheduling requests.
3. **`SkillUsingCoordinatorAgent`**:
   - Combines the Lab 2 tool layer (`InboxReaderTool`, `ContactsPriorRepliesTool`, `UrgencyDomainCalculatorTool`) with `PlanningSkill` and `FormattingSkill`.
   - Executes arbitrary faculty triage workflows driven purely by schemas without hardcoding case logic.

## Acceptance Criteria (Chapter 3 PDF)
> **Acceptance**: Two callable skills with schemas, invoked by the agent. The same skill works for two different cases without code changes.

## How to Run the Demo
```bash
python lab03_skills/demo_lab03.py
```

## Proof of Acceptance
When executing `demo_lab03.py`:
- The exact same instances of `PlanningSkill` and `FormattingSkill` are invoked for:
  - **Case 1**: Mid-semester Student Advising & Office Hours Workload (prioritizing students, thesis advising templates, office hours matching).
  - **Case 2**: Faculty Senate & Research Grants Workload (prioritizing administrative deadlines, curriculum reviews, and partner research co-investigators).
- Both cases produce locked plans (`assert plan.locked is True`).
- Both cases generate complete `FormattedDocument` objects containing all 4 Dashboard panels.
- Zero lines of skill code are altered between the two cases, proving full case-agnostic reusability.
