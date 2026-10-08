"""Lab 3 Demonstration Script: Skill Creation — Reusable Plan & Format Skills.

Proves acceptance criteria from Chapter 3:
"Two callable skills with schemas, invoked by the agent.
Accept: The same skill works for two different cases without code changes."

Interface signatures validated:
  skill plan(inputs) -> Plan: return expand(inputs).lock()
  skill format_triaged(result, template) -> Document
"""

from __future__ import annotations
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab03_skills.skills import (
    PlanningSkill,
    FormattingSkill,
    PlanSkillInput,
    TemplateSpec,
    OutputFormat,
)
from lab03_skills.agent import SkillUsingCoordinatorAgent


def main():
    print("=" * 75)
    print("LAB 3: Skill Creation — Reusable Plan & Format Skills")
    print("=" * 75)

    # Instantiate the reusable skills ONCE
    planning_skill = PlanningSkill()
    formatting_skill = FormattingSkill()

    # Instantiate the coordinator agent wired with these skills
    agent = SkillUsingCoordinatorAgent(
        planning_skill=planning_skill,
        formatting_skill=formatting_skill,
    )

    # =========================================================================
    # CASE 1: Teaching & Student Advising Triage
    # =========================================================================
    print("\n" + "#" * 75)
    print("CASE 1: Teaching & Student Advising Workload")
    print("#" * 75)

    case_1_input = PlanSkillInput(
        case_name="CS Student Advising & Office Hours",
        time_window="past 24 hours",
        scope_filter="undergraduate inquiries & PhD thesis advisees",
        priority_sender_categories=["student"],
        include_draft_replies=True,
        include_action_item_extraction=True,
        include_calendar_sync=True,
        standard_template_focus="thesis_advising_response",
        custom_rules=[
            "Flag thesis defense committee approval forms as URGENT",
            "Match student meeting requests to Wednesday office hours calendar",
        ]
    )

    case_1_template = TemplateSpec(
        template_name="Student Advising Digest Template",
        output_format=OutputFormat.MARKDOWN,
        header_title="Faculty Advising & Office Hours Triage Dashboard",
        include_summary_banner=True,
        include_inbox_panel=True,
        include_drafts_panel=True,
        include_actions_panel=True,
        include_followup_panel=True,
        highlight_category="student"
    )

    print(f"\n[Case 1 Plan Input Schema]:\n  Case Name: {case_1_input.case_name}")
    print(f"  Scope: {case_1_input.scope_filter}")
    print(f"  Priority Categories: {case_1_input.priority_sender_categories}")
    print(f"  Template Focus: {case_1_input.standard_template_focus}")

    # Run Case 1
    plan_1, inbox_1, doc_1 = agent.run_case(case_1_input, case_1_template)

    print(f"\n[Case 1 Plan Output]:")
    print(f"  Plan ID: {plan_1.plan_id}")
    print(f"  Target Scope: {plan_1.target_scope}")
    print(f"  Is Locked: {plan_1.locked} (Mandatory: return expand(inputs).lock())")
    print(f"  Step Count: {len(plan_1.steps)}")
    for s in plan_1.steps:
        print(f"    - Step {s.step_id} [{s.name}]: {s.description[:65]}...")

    print(f"\n[Case 1 Formatted Document Generated]:")
    print(f"  Document ID: {doc_1.document_id}")
    print(f"  Title: {doc_1.title}")
    print(f"  Format: {doc_1.format.value}")
    print(f"  Total Items Processed: {doc_1.item_count}")
    print(f"  Rendered Panels: {list(doc_1.panels.keys())}")

    # Validate Case 1
    assert plan_1.locked is True, "Case 1 plan must be locked."
    assert "student" in plan_1.parameters["priority_sender_categories"]
    assert "triaged_inbox" in doc_1.panels
    assert "draft_queue" in doc_1.panels
    assert "action_items" in doc_1.panels
    assert "followup_digest" in doc_1.panels
    print("\n[Case 1 Validation Passed Successfully]")

    # =========================================================================
    # CASE 2: Faculty Senate & Research Grants Triage
    # =========================================================================
    print("\n" + "#" * 75)
    print("CASE 2: Faculty Senate & Research Operations Workload")
    print("#" * 75)

    case_2_input = PlanSkillInput(
        case_name="Faculty Senate & Grant Collaborations",
        time_window="past 72 hours",
        scope_filter="Dean's office, curriculum committees, research co-investigators",
        priority_sender_categories=["admin", "collaborator"],
        include_draft_replies=True,
        include_action_item_extraction=True,
        include_calendar_sync=False,
        standard_template_focus="admin_acknowledgement",
        custom_rules=[
            "Curriculum review submission deadline tomorrow is priority 1",
            "Quantum simulation manuscript revisions flagged for partner review",
        ]
    )

    case_2_template = TemplateSpec(
        template_name="Administrative Governance Template",
        output_format=OutputFormat.MARKDOWN,
        header_title="Faculty Senate & Research Governance Executive Brief",
        include_summary_banner=True,
        include_inbox_panel=True,
        include_drafts_panel=True,
        include_actions_panel=True,
        include_followup_panel=True,
        highlight_category="admin"
    )

    print(f"\n[Case 2 Plan Input Schema]:\n  Case Name: {case_2_input.case_name}")
    print(f"  Scope: {case_2_input.scope_filter}")
    print(f"  Priority Categories: {case_2_input.priority_sender_categories}")
    print(f"  Template Focus: {case_2_input.standard_template_focus}")

    # Run Case 2 through the EXACT SAME skill instances
    plan_2, inbox_2, doc_2 = agent.run_case(case_2_input, case_2_template)

    print(f"\n[Case 2 Plan Output]:")
    print(f"  Plan ID: {plan_2.plan_id}")
    print(f"  Target Scope: {plan_2.target_scope}")
    print(f"  Is Locked: {plan_2.locked} (Mandatory: return expand(inputs).lock())")
    print(f"  Step Count: {len(plan_2.steps)}")
    for s in plan_2.steps:
        print(f"    - Step {s.step_id} [{s.name}]: {s.description[:65]}...")

    print(f"\n[Case 2 Formatted Document Generated]:")
    print(f"  Document ID: {doc_2.document_id}")
    print(f"  Title: {doc_2.title}")
    print(f"  Format: {doc_2.format.value}")
    print(f"  Total Items Processed: {doc_2.item_count}")
    print(f"  Rendered Panels: {list(doc_2.panels.keys())}")

    # Validate Case 2
    assert plan_2.locked is True, "Case 2 plan must be locked."
    assert "admin" in plan_2.parameters["priority_sender_categories"]
    assert "collaborator" in plan_2.parameters["priority_sender_categories"]
    assert "triaged_inbox" in doc_2.panels
    assert "draft_queue" in doc_2.panels
    assert "action_items" in doc_2.panels
    print("\n[Case 2 Validation Passed Successfully]")

    # =========================================================================
    # Direct Skill Callable Interface Verification (Exact Chapter 3 Pseudocode)
    # =========================================================================
    print("\n" + "-" * 75)
    print("DIRECT SKILL CALLABLE INTERFACE VERIFICATION (Pseudocode Signatures)")
    print("-" * 75)
    print("  skill plan(inputs) -> Plan: return expand(inputs).lock()")
    direct_plan = planning_skill.plan(case_1_input)
    assert direct_plan.locked is True
    print(f"  -> Direct PlanningSkill call returned locked plan: {direct_plan.plan_id} (locked={direct_plan.locked})")

    print("\n  skill format_triaged(result, template) -> Document")
    # Also verify alternative HTML output format via TemplateSpec
    html_template = TemplateSpec(
        template_name="HTML Email Digest",
        output_format=OutputFormat.HTML,
        header_title="Dean's Weekly Email Brief"
    )
    direct_doc = formatting_skill.format_triaged(inbox_2, html_template)
    assert direct_doc.format == OutputFormat.HTML
    assert "<table border='1'" in direct_doc.rendered_content
    print(f"  -> Direct FormattingSkill call rendered HTML Document: {direct_doc.document_id}")

    # =========================================================================
    # Display Sample Rendered Markdown Output (Panel Previews)
    # =========================================================================
    print("\n" + "=" * 75)
    print("SAMPLE OUTPUT PREVIEW: Case 1 Rendered Markdown Panels")
    print("=" * 75)
    # Print the top 45 lines of the rendered document for inspection
    lines = doc_1.rendered_content.split("\n")
    for line in lines[:45]:
        print(line)
    if len(lines) > 45:
        print(f"... [{len(lines) - 45} more lines generated in doc_1] ...")

    # =========================================================================
    # Final Acceptance Assertions
    # =========================================================================
    print("\n" + "=" * 75)
    print("ACCEPTANCE VERIFICATION:")
    print("1. Two callable skills with schemas (PlanningSkill & FormattingSkill): VERIFIED")
    print("2. Interfaces match spec: plan(inputs) -> Plan and format_triaged(result, template) -> Document: VERIFIED")
    print("3. Reusable across cases: Tested Case 1 (Teaching) & Case 2 (Senate/Research): VERIFIED")
    print("4. Code changes required between cases: 0 (ZERO): VERIFIED")
    print("=" * 75)
    print("ALL LAB 3 ACCEPTANCE CRITERIA SATISFIED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
