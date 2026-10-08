"""Lab 3: Skill Creation — Reusable Plan & Format Skills.

Implements the Lab 3 Chapter 3 specification:
- Package repeatable capability as reusable, schema-typed skills.
- Planning skill: skill plan(inputs) -> Plan: return expand(inputs).lock()
- Formatting skill: skill format_triaged(result, template) -> Document
- Case-agnostic design: identical skills work across multiple cases without code changes.
"""

from __future__ import annotations
import uuid
import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from core.models import (
    ExecutionPlan,
    PlanStep,
    TriagedInbox,
    TriagedEmail,
    DraftReply,
    ActionItem,
    MeetingRequest,
    SenderCategory,
    UrgencyLevel,
    ApprovalStatus,
)


# =====================================================================
# 1. PLANNING SKILL SCHEMAS & IMPLEMENTATION
# =====================================================================

class PlanSkillInput(BaseModel):
    """Typed schema for planning skill inputs."""
    case_name: str = Field(description="Descriptive identifier for this triage case")
    time_window: str = Field(default="past 24 hours", description="Time window or date scope for email retrieval")
    scope_filter: str = Field(default="all faculty mail", description="Target inbox scope or sender filter")
    priority_sender_categories: List[str] = Field(
        default_factory=list,
        description="Sender categories to elevate in urgency ranking (e.g. ['student', 'admin'])"
    )
    include_draft_replies: bool = Field(default=True, description="Whether to generate draft replies")
    include_action_item_extraction: bool = Field(default=True, description="Whether to extract action items & tasks")
    include_calendar_sync: bool = Field(default=True, description="Whether to match meeting requests with calendar slots")
    standard_template_focus: Optional[str] = Field(
        default=None,
        description="Preferred standard response library or template category"
    )
    custom_rules: List[str] = Field(default_factory=list, description="Explicit faculty handling rules or constraints")
    extra_parameters: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary case-specific parameters")


class PlanningSkill:
    """Reusable, schema-typed Planning / Blueprint skill.
    
    Implements: skill plan(inputs) -> Plan: return expand(inputs).lock()
    """

    def plan(self, inputs: PlanSkillInput) -> ExecutionPlan:
        """Expands the input specification into a structured workflow and locks it."""
        return self._expand(inputs).lock()

    def _expand(self, inputs: PlanSkillInput) -> _PlanBuilder:
        """Expands input parameters into ordered, case-appropriate execution steps."""
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        steps: List[PlanStep] = []
        step_counter = 1

        # Step 1: Ingestion & Classification
        filter_summary = f"Scope: [{inputs.scope_filter}], Window: [{inputs.time_window}]"
        steps.append(
            PlanStep(
                step_id=step_counter,
                name="Ingestion & Classification",
                description=f"Ingest email threads for {filter_summary}. Classify senders into canonical categories."
            )
        )
        step_counter += 1

        # Step 2: Priority & Urgency Ranking
        priority_rule_desc = ""
        if inputs.priority_sender_categories:
            cats = ", ".join(inputs.priority_sender_categories)
            priority_rule_desc += f" Boost categories: [{cats}]."
        if inputs.custom_rules:
            rules_str = "; ".join(inputs.custom_rules)
            priority_rule_desc += f" Custom rules: [{rules_str}]."

        steps.append(
            PlanStep(
                step_id=step_counter,
                name="Priority & Urgency Scoring",
                description=f"Evaluate deadline signals, escalation phrases, and sender roles.{priority_rule_desc}"
            )
        )
        step_counter += 1

        # Step 3: Draft Reply Generation
        if inputs.include_draft_replies:
            template_info = f" Focus library: [{inputs.standard_template_focus}]." if inputs.standard_template_focus else ""
            steps.append(
                PlanStep(
                    step_id=step_counter,
                    name="Draft Reply Generation",
                    description=f"Propose candidate replies grounded in thread history and standard templates.{template_info}"
                )
            )
            step_counter += 1

        # Step 4: Extraction & Calendar Matching
        if inputs.include_action_item_extraction or inputs.include_calendar_sync:
            parts = []
            if inputs.include_action_item_extraction:
                parts.append("extract commitments and deadline tasks")
            if inputs.include_calendar_sync:
                parts.append("cross-reference meeting requests with faculty calendar availability")
            steps.append(
                PlanStep(
                    step_id=step_counter,
                    name="Action-Item & Calendar Sync",
                    description=f"Analyze thread bodies to {' and '.join(parts)}."
                )
            )
            step_counter += 1

        # Step 5: Acceptance Validation Gate
        steps.append(
            PlanStep(
                step_id=step_counter,
                name="Validation Gate",
                description="Enforce acceptance checks: verify citations, confirm no-auto-send policy, ensure data stays in-account."
            )
        )
        step_counter += 1

        # Step 6: Faculty Review & Governed Release
        steps.append(
            PlanStep(
                step_id=step_counter,
                name="Faculty Review & Approval",
                description=f"Present triaged inbox to mailbox owner for final approval/edit/override for case '{inputs.case_name}'."
            )
        )

        plan = ExecutionPlan(
            plan_id=plan_id,
            target_scope=f"{inputs.case_name} ({inputs.time_window})",
            parameters=inputs.model_dump(),
            steps=steps,
            locked=False
        )
        return _PlanBuilder(plan)


class _PlanBuilder:
    """Helper wrapper that supports chaining .lock()."""
    def __init__(self, plan: ExecutionPlan):
        self._plan = plan

    def lock(self) -> ExecutionPlan:
        self._plan.locked = True
        return self._plan


# =====================================================================
# 2. FORMATTING SKILL SCHEMAS & IMPLEMENTATION
# =====================================================================

class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"


class TemplateSpec(BaseModel):
    """Configuration for rendering the Section 3.9 Dashboard panels."""
    template_name: str = Field(description="Name of the formatting template")
    output_format: OutputFormat = Field(default=OutputFormat.MARKDOWN, description="Format syntax to render")
    header_title: Optional[str] = Field(default=None, description="Custom document title banner")
    include_summary_banner: bool = Field(default=True, description="Include executive metric banner")
    include_inbox_panel: bool = Field(default=True, description="Include Triaged Inbox panel")
    include_drafts_panel: bool = Field(default=True, description="Include Draft-Reply Queue panel")
    include_actions_panel: bool = Field(default=True, description="Include Action-Item List panel")
    include_followup_panel: bool = Field(default=True, description="Include Follow-up Digest panel")
    highlight_category: Optional[str] = Field(default=None, description="Category to visually highlight in tables")


class FormattedDocument(BaseModel):
    """Typed output of the formatting skill."""
    document_id: str
    title: str
    format: OutputFormat
    rendered_content: str
    panels: Dict[str, str] = Field(default_factory=dict)
    item_count: int = 0
    generated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FormattingSkill:
    """Reusable, schema-typed Formatting skill.
    
    Implements: skill format_triaged(result, template) -> Document
    Renders Section 3.9 Dashboard panels:
    - Triaged inbox: Emails ranked by sender category and urgency.
    - Draft-reply queue: Proposed replies awaiting faculty approval.
    - Action-item list: Tasks, deadlines, and commitments extracted from mail.
    - Follow-up digest: 'Reply later' items resurfacing on schedule, plus response-time metrics.
    """

    def format_triaged(self, result: TriagedInbox, template: TemplateSpec) -> FormattedDocument:
        """Renders triaged inbox data into a formatted document according to template spec."""
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        title = template.header_title or f"Triaged Inbox Digest — Run {result.run_id}"

        # Sort items by urgency score descending
        sorted_items = sorted(result.items, key=lambda x: x.urgency_score, reverse=True)

        panels: Dict[str, str] = {}
        rendered_sections: List[str] = []

        if template.output_format == OutputFormat.MARKDOWN:
            # Title Banner
            rendered_sections.append(f"# {title}\n")
            rendered_sections.append(f"> **Status**: `{result.status.value.upper()}` | **Version**: `v{result.version}` | **Generated**: `{result.timestamp}`\n")

            # Summary Metrics Banner
            if template.include_summary_banner:
                total = len(sorted_items)
                urgent_count = sum(1 for i in sorted_items if i.urgency == UrgencyLevel.URGENT)
                high_count = sum(1 for i in sorted_items if i.urgency == UrgencyLevel.HIGH)
                draft_count = sum(1 for i in sorted_items if i.draft_reply is not None)
                action_count = sum(len(i.action_items) for i in sorted_items)

                summary_md = (
                    "### [SUMMARY] Executive Metrics\n\n"
                    f"- **Total Threads Processed**: {total}\n"
                    f"- **Urgent / High Priority**: {urgent_count} Urgent / {high_count} High\n"
                    f"- **Draft Replies Staged**: {draft_count} (Requires Faculty Sign-off)\n"
                    f"- **Action Items Extracted**: {action_count}\n"
                )
                panels["summary"] = summary_md
                rendered_sections.append(summary_md)

            # Panel 1: Triaged Inbox
            if template.include_inbox_panel:
                inbox_lines = ["## [PANEL 1] Triaged Inbox (Ranked by Category & Urgency)\n"]
                inbox_lines.append("| Rank | Score | Urgency | Category | Sender | Subject | Rationale |")
                inbox_lines.append("|---|---|---|---|---|---|---|")
                for rank, item in enumerate(sorted_items, 1):
                    hl = " *" if template.highlight_category and item.category.value == template.highlight_category else ""
                    inbox_lines.append(
                        f"| {rank} | **{item.urgency_score}/100** | `{item.urgency.value.upper()}` | "
                        f"{item.category.value.capitalize()}{hl} | `{item.sender}` | {item.subject} | {item.rationale} |"
                    )
                inbox_panel_md = "\n".join(inbox_lines) + "\n"
                panels["triaged_inbox"] = inbox_panel_md
                rendered_sections.append(inbox_panel_md)

            # Panel 2: Draft-Reply Queue
            if template.include_drafts_panel:
                drafts_lines = ["## [PANEL 2] Draft-Reply Queue (Awaiting Faculty Approval)\n"]
                draft_items = [i for i in sorted_items if i.draft_reply]
                if not draft_items:
                    drafts_lines.append("_No pending draft replies._\n")
                else:
                    for i in draft_items:
                        d = i.draft_reply
                        citations_str = ", ".join(d.citations) if d.citations else "Direct email thread"
                        tmpl_str = f"`{d.template_used}`" if d.template_used else "_Generated without template_"
                        drafts_lines.append(f"### Draft for Thread `{d.thread_id}`: {d.subject}")
                        drafts_lines.append(f"- **Recipient**: `{d.recipient}`")
                        drafts_lines.append(f"- **Template Applied**: {tmpl_str}")
                        drafts_lines.append(f"- **Citations / Context**: {citations_str}")
                        drafts_lines.append(f"- **Review Status**: `{d.status.value.upper()}` (Hard Gate: Never sent without approval)")
                        drafts_lines.append("\n```text")
                        drafts_lines.append(d.body.strip())
                        drafts_lines.append("```\n")
                drafts_panel_md = "\n".join(drafts_lines)
                panels["draft_queue"] = drafts_panel_md
                rendered_sections.append(drafts_panel_md)

            # Panel 3: Action-Item List
            if template.include_actions_panel:
                action_lines = ["## [PANEL 3] Action-Item List (Tasks & Commitments)\n"]
                action_lines.append("| ID | Thread | Task | Deadline | Owner | Confirmed |")
                action_lines.append("|---|---|---|---|---|---|")
                total_actions = 0
                for item in sorted_items:
                    for act in item.action_items:
                        total_actions += 1
                        deadline_str = act.deadline if act.deadline else "None specified"
                        conf_str = "[YES]" if act.confirmed else "[PENDING]"
                        action_lines.append(
                            f"| `{act.item_id}` | `{act.thread_id}` | {act.task} | **{deadline_str}** | {act.owner} | {conf_str} |"
                        )
                if total_actions == 0:
                    action_lines.append("| - | - | _No actionable commitments detected_ | - | - | - |")
                action_panel_md = "\n".join(action_lines) + "\n"
                panels["action_items"] = action_panel_md
                rendered_sections.append(action_panel_md)

            # Panel 4: Follow-up Digest
            if template.include_followup_panel:
                followup_lines = ["## [PANEL 4] Follow-up Digest ('Reply Later' & Scheduling)\n"]
                followups = [i for i in sorted_items if i.reply_later or i.meeting_request]
                if not followups:
                    followup_lines.append("_No threads flagged for reply-later or scheduling._\n")
                else:
                    for f in followups:
                        if f.reply_later:
                            resurface = f.resurface_date or "Next scheduled triage cycle"
                            followup_lines.append(f"- **[Reply Later]** `{f.thread_id}` ({f.subject}) -> Resurface: `{resurface}`")
                        if f.meeting_request:
                            mr = f.meeting_request
                            slots_str = "; ".join(mr.proposed_slots) if mr.proposed_slots else "Awaiting slot proposal"
                            status_str = "Confirmed" if mr.confirmed_by_faculty else "Pending Faculty Sign-off"
                            followup_lines.append(f"- **[Meeting Request]** `{mr.subject}` from `{mr.sender}` -> Proposed: [{slots_str}] ({status_str})")
                followup_panel_md = "\n".join(followup_lines) + "\n"
                panels["followup_digest"] = followup_panel_md
                rendered_sections.append(followup_panel_md)

        elif template.output_format == OutputFormat.TEXT:
            # Plain Text formatting
            rendered_sections.append(f"=== {title.upper()} ===")
            rendered_sections.append(f"Status: {result.status.value.upper()} | Generated: {result.timestamp}\n")
            for rank, item in enumerate(sorted_items, 1):
                rendered_sections.append(f"[{rank}] {item.urgency.value.upper()} ({item.urgency_score}/100) | {item.category.value} | {item.sender}")
                rendered_sections.append(f"    Subject: {item.subject}")
                rendered_sections.append(f"    Rationale: {item.rationale}")
                if item.draft_reply:
                    rendered_sections.append(f"    Draft Reply to {item.draft_reply.recipient}:\n    \"{item.draft_reply.body[:80]}...\"")
                if item.action_items:
                    for act in item.action_items:
                        rendered_sections.append(f"    Action: {act.task} (Deadline: {act.deadline})")
                rendered_sections.append("-" * 60)
            panels["full_text"] = "\n".join(rendered_sections)

        elif template.output_format == OutputFormat.HTML:
            # Clean HTML format
            html_parts = [f"<div class='email-organizer-digest'><h1>{title}</h1>"]
            html_parts.append(f"<p><em>Status: {result.status.value.upper()} | Version: v{result.version}</em></p>")
            html_parts.append("<table border='1' cellpadding='6' cellspacing='0'>")
            html_parts.append("<tr><th>Rank</th><th>Score</th><th>Urgency</th><th>Category</th><th>Sender</th><th>Subject</th></tr>")
            for rank, item in enumerate(sorted_items, 1):
                html_parts.append(
                    f"<tr><td>{rank}</td><td>{item.urgency_score}</td><td>{item.urgency.value}</td>"
                    f"<td>{item.category.value}</td><td>{item.sender}</td><td>{item.subject}</td></tr>"
                )
            html_parts.append("</table></div>")
            rendered_sections.append("\n".join(html_parts))
            panels["html_body"] = "\n".join(html_parts)

        rendered_full = "\n".join(rendered_sections)

        return FormattedDocument(
            document_id=doc_id,
            title=title,
            format=template.output_format,
            rendered_content=rendered_full,
            panels=panels,
            item_count=len(sorted_items),
            metadata={
                "run_id": result.run_id,
                "template_name": template.template_name,
                "timestamp": result.timestamp,
            }
        )
