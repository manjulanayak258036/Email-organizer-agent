"""Lab 3: Skill-Using Coordinator Agent.

Integrates typed tools (from Lab 2) with schema-typed, reusable skills (Lab 3):
- PlanningSkill: plan(inputs) -> Plan (locked)
- FormattingSkill: format_triaged(result, template) -> Document
"""

from __future__ import annotations
import uuid
import datetime
from typing import List, Dict, Any, Optional, Tuple

from core.classifier import classify_sender
from core.models import (
    ExecutionPlan,
    TriagedInbox,
    TriagedEmail,
    DraftReply,
    ActionItem,
    MeetingRequest,
    SenderCategory,
    UrgencyLevel,
    ApprovalStatus,
    EmailThread,
)
from lab02_tools.tools import (
    InboxReaderTool,
    ContactsPriorRepliesTool,
    UrgencyDomainCalculatorTool,
    ComputedDomainMetrics,
)
from lab03_skills.skills import (
    PlanningSkill,
    FormattingSkill,
    PlanSkillInput,
    TemplateSpec,
    FormattedDocument,
)


class SkillUsingCoordinatorAgent:
    """Coordinator Agent that leverages reusable planning and formatting skills."""

    def __init__(
        self,
        planning_skill: Optional[PlanningSkill] = None,
        formatting_skill: Optional[FormattingSkill] = None,
        inbox_tool: Optional[InboxReaderTool] = None,
        contacts_tool: Optional[ContactsPriorRepliesTool] = None,
        calculator_tool: Optional[UrgencyDomainCalculatorTool] = None,
    ):
        self.planning_skill = planning_skill or PlanningSkill()
        self.formatting_skill = formatting_skill or FormattingSkill()
        self.inbox_tool = inbox_tool or InboxReaderTool()
        self.contacts_tool = contacts_tool or ContactsPriorRepliesTool()
        self.calculator_tool = calculator_tool or UrgencyDomainCalculatorTool()

    def run_case(
        self,
        plan_input: PlanSkillInput,
        template_spec: TemplateSpec,
        threads: Optional[List[EmailThread]] = None,
        contacts: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[ExecutionPlan, TriagedInbox, FormattedDocument]:
        """Executes the end-to-end skill-driven workflow for any arbitrary case."""
        # 1. Execute Planning Skill
        # skill plan(inputs) -> Plan: return expand(inputs).lock()
        locked_plan = self.planning_skill.plan(plan_input)
        assert locked_plan.locked, "Violation: Plan must be locked before pipeline proceeds."

        # 2. Ingest data through typed tools (Lab 2 pattern)
        raw_threads = threads if threads is not None else self.inbox_tool.read()
        known_contacts = contacts if contacts is not None else self.contacts_tool.read()

        # Compute verified domain metrics via typed checker
        computed_metrics: ComputedDomainMetrics = self.calculator_tool.compute(raw_threads, known_contacts)
        assert computed_metrics.valid, f"Validation failure: {computed_metrics.validation_notes}"

        # 3. Assemble triaged inbox grounded in plan parameters and computed metrics
        triaged_inbox = self._assemble_triaged_inbox(locked_plan, raw_threads, known_contacts, computed_metrics)

        # 4. Execute Formatting Skill
        # skill format_triaged(result, template) -> Document
        formatted_doc = self.formatting_skill.format_triaged(triaged_inbox, template_spec)

        return locked_plan, triaged_inbox, formatted_doc

    def _assemble_triaged_inbox(
        self,
        plan: ExecutionPlan,
        threads: List[EmailThread],
        contacts: List[Dict[str, Any]],
        metrics: ComputedDomainMetrics,
    ) -> TriagedInbox:
        """Assembles the TriagedInbox adhering to the locked plan parameters."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        contact_map = {c["contact"].lower(): c for c in contacts}
        params = plan.parameters

        priority_categories = params.get("priority_sender_categories", [])
        include_drafts = params.get("include_draft_replies", True)
        template_focus = params.get("standard_template_focus")

        triaged_items: List[TriagedEmail] = []

        for th in threads:
            sender_lower = th.sender.lower()
            matched_contact = contact_map.get(sender_lower)

            # Determine category via the shared configurable classifier.
            if matched_contact:
                category_val = matched_contact.get("category", "other")
                try:
                    category = SenderCategory(category_val)
                except ValueError:
                    category = classify_sender(th.sender, contact_map)
            else:
                category = classify_sender(th.sender, contact_map)

            # Base score from typed calculator tool
            score = metrics.per_thread_scores.get(th.thread_id, 20)

            # Apply plan-specific category priority boost if specified in plan
            if category.value in priority_categories:
                score = min(100, score + 15)

            # Assign tier
            if score >= 70:
                tier = UrgencyLevel.URGENT
            elif score >= 45:
                tier = UrgencyLevel.HIGH
            elif score >= 20:
                tier = UrgencyLevel.MEDIUM
            else:
                tier = UrgencyLevel.LOW

            # Extract Action Items
            action_items: List[ActionItem] = []
            combined_body = " ".join(m.body for m in th.messages)
            combined_lower = combined_body.lower()

            if "deadline" in combined_lower or "due" in combined_lower or "submit" in combined_lower:
                deadline_str = "Friday 5:00 PM" if "friday" in combined_lower else "Tomorrow 3:00 PM"
                action_items.append(
                    ActionItem(
                        item_id=f"act_{th.thread_id[:12]}_{len(action_items)+1}",
                        thread_id=th.thread_id,
                        task=f"Review and sign submission for '{th.subject}'",
                        deadline=deadline_str,
                        owner="Faculty Mailbox Owner",
                        confirmed=False  # Hard guardrail: never mark complete without confirmation
                    )
                )

            # Extract Meeting Request
            meeting_req: Optional[MeetingRequest] = None
            if "office hours" in combined_lower or "meet" in combined_lower or "schedule" in combined_lower:
                meeting_req = MeetingRequest(
                    request_id=f"mtg_{th.thread_id[:12]}",
                    thread_id=th.thread_id,
                    sender=th.sender,
                    subject=th.subject,
                    proposed_slots=["Wednesday at 2:30 PM", "Thursday at 11:00 AM"],
                    confirmed_by_faculty=False  # Hard guardrail: never confirm without approval
                )

            # Propose Draft Reply (Draft only — never auto-sent)
            draft_reply: Optional[DraftReply] = None
            draft_status_note: Optional[str] = None
            if include_drafts and category != SenderCategory.VENDOR and self.calculator_tool.should_generate_reply(th, category):
                if matched_contact and matched_contact.get("standard_template"):
                    template_name = matched_contact["standard_template"]
                elif template_focus and category.value in priority_categories:
                    template_name = template_focus
                else:
                    category_defaults = {
                        SenderCategory.STUDENT: "student_advising_response",
                        SenderCategory.ADMIN: "admin_acknowledgement",
                        SenderCategory.COLLABORATOR: "research_collaboration",
                    }
                    template_name = category_defaults.get(category, "standard_acknowledgement")
                citations = [f"Thread {th.thread_id}", f"Sender: {th.sender}"]
                
                if category == SenderCategory.STUDENT:
                    body = (
                        f"Dear {th.sender.split('@')[0].replace('.', ' ').title()},\n\n"
                        f"Thank you for reaching out regarding '{th.subject}'. I have reviewed your note. "
                        "Please see the posted course notes / guidelines, and let me know if you would like to follow up during office hours.\n\n"
                        "Best regards,\nEleanor Vance"
                    )
                elif category == SenderCategory.ADMIN:
                    body = (
                        "Colleagues,\n\n"
                        f"Acknowledging receipt of the notice regarding '{th.subject}'. I am finalizing our department review and will submit prior to the deadline.\n\n"
                        "Best regards,\nEleanor Vance"
                    )
                else:
                    body = (
                        f"Hi,\n\n"
                        f"Thanks for your message on '{th.subject}'. I will review the materials in detail and get back to you shortly.\n\n"
                        "Best,\nEleanor Vance"
                    )

                draft_reply = DraftReply(
                    draft_id=f"drf_{th.thread_id[:12]}",
                    thread_id=th.thread_id,
                    recipient=th.sender,
                    subject=f"Re: {th.subject}",
                    body=body,
                    template_used=template_name,
                    citations=citations,
                    status=ApprovalStatus.DRAFT,
                    approved_by=None,
                )
            elif include_drafts and category != SenderCategory.VENDOR:
                draft_status_note = "No reply needed — informational"

            rationale = f"Categorized as {category.value.capitalize()} with score {score}/100. Action items detected: {len(action_items)}."

            triaged_items.append(
                TriagedEmail(
                    thread_id=th.thread_id,
                    subject=th.subject,
                    sender=th.sender,
                    category=category,
                    urgency=tier,
                    urgency_score=score,
                    rationale=rationale,
                    action_items=action_items,
                    meeting_request=meeting_req,
                    draft_reply=draft_reply,
                    draft_status_note=draft_status_note,
                    reply_later=(tier == UrgencyLevel.LOW),
                    resurface_date="2026-09-22T09:00:00Z" if tier == UrgencyLevel.LOW else None
                )
            )

        return TriagedInbox(
            run_id=run_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            items=triaged_items,
            version=1,
            status=ApprovalStatus.DRAFT
        )
