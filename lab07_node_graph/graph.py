"""Lab 7: Agentic Node Graph - the full pipeline.

The graph layer wires the Phase-A components into the Chapter 3 topology:

    ingest -> plan -> workers -> validate
                        ^          |
                        | fail     | pass
                        +----------+
                                   -> assemble -> gate -> publish

Execution, audit, budget, approval, and checkpoint behavior stays inside
Lab 6's GovernedRuntime. This module only owns graph topology and the bounded
validation retry edge.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.classifier import classify_sender
from core.models import (
    ActionItem,
    ApprovalStatus,
    DraftReply,
    EmailThread,
    MeetingRequest,
    SenderCategory,
    TriagedEmail,
    TriagedInbox,
    UrgencyLevel,
)
from lab02_tools.tools import UrgencyDomainCalculatorTool
from lab03_skills.skills import PlanningSkill, PlanSkillInput, FormattingSkill, TemplateSpec
from lab05_connector.connector import MCPStyleConnector, build_connector
from lab06_runtime.runtime import GovernedRuntime, RuntimeNode, StepStatus
from lab13_specialists.registry import registry
from lab13_specialists.specialists import GenerationAgent


class ValidationReport(BaseModel):
    """Validation output for the graph hard gate."""

    passed: bool
    attempt: int
    errors: List[str] = Field(default_factory=list)
    item_count: int = 0
    draft_count: int = 0


class GraphRunResult(BaseModel):
    """Serializable summary of a graph run."""

    run_id: str
    status: str
    triaged_inbox: Optional[TriagedInbox] = None
    validation_report: Optional[ValidationReport] = None
    attempts_used: int = 0
    max_retries: int = 0
    retry_events: List[str] = Field(default_factory=list)
    graph_trace: List[Dict[str, Any]] = Field(default_factory=list)
    formatted_preview: Optional[str] = None
    source_backend: str = "unknown"
    specialist_registry_summary: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class AgenticNodeGraph:
    """Explicit Lab 7 graph runner backed by GovernedRuntime."""

    def __init__(
        self,
        connector: Optional[MCPStyleConnector] = None,
        runtime: Optional[GovernedRuntime] = None,
        max_retries: int = 2,
    ):
        self.connector = connector or build_connector()
        self.runtime = runtime or GovernedRuntime(
            run_id=f"lab07-{uuid.uuid4().hex[:8]}",
            audit_path="audit_log.jsonl",
            checkpoint_path="runtime_checkpoint.jsonl",
            total_budget=150.0,
            auto_approve=True,
            approver="Faculty Mailbox Owner",
        )
        self.max_retries = max_retries
        self.state: Dict[str, Any] = {}
        self.retry_events: List[str] = []
        self._registered = False

        self.ingest_node = RuntimeNode(node_id="ingest", name="IngestionClassificationAgent", fn=self._ingest, budget_limit=25.0)
        self.plan_node = RuntimeNode(node_id="plan", name="CoordinatorPlanNode", fn=self._plan, budget_limit=15.0)
        self.workers_node = RuntimeNode(node_id="workers", name="WorkerAgents", fn=self._workers, budget_limit=40.0)
        self.validate_node = RuntimeNode(node_id="validate", name="ValidationGate", fn=self._validate, budget_limit=20.0)
        self.assemble_node = RuntimeNode(node_id="assemble", name="AssemblyNode", fn=self._assemble, budget_limit=20.0)
        self.gate_node = RuntimeNode(
            node_id="gate",
            name="MailboxOwnerGate",
            fn=self._gate_summary,
            requires_approval=True,
            budget_limit=10.0,
        )
        self.publish_node = RuntimeNode(node_id="publish", name="GovernedPublishNode", fn=self._publish, budget_limit=10.0)

    def run(
        self,
        max_results: int = 5,
        query: str = "label:INBOX",
        inject_validation_failure_once: bool = False,
        force_validation_failure: bool = False,
    ) -> GraphRunResult:
        """Run the graph once, including the bounded validation retry edge."""
        self._register_nodes()
        self.state = {
            "query": query,
            "max_results": max_results,
            "inject_validation_failure_once": inject_validation_failure_once,
            "force_validation_failure": force_validation_failure,
            "failure_injected": False,
        }
        self.retry_events = []

        self._run_node(self.ingest_node, {"query": query, "max_results": max_results})
        self._run_node(self.plan_node, {"case_name": "Lab 7 Full Pipeline"})

        validation_report: Optional[ValidationReport] = None
        attempts_used = 0
        max_attempts = self.max_retries + 1

        for attempt in range(1, max_attempts + 1):
            attempts_used = attempt
            self.state["attempt"] = attempt
            self._run_node(self.workers_node, {"attempt": attempt})
            self._run_node(self.validate_node, {"attempt": attempt})
            validation_report = self.state["validation_report"]

            if validation_report.passed:
                break

            if attempt <= self.max_retries:
                event = f"validate --fail--> workers (attempt {attempt}/{max_attempts})"
                self.retry_events.append(event)
                continue

            event = f"bounded retry exhausted after {attempt} attempts"
            self.retry_events.append(event)
            return self._result(
                status="failed_validation",
                attempts_used=attempts_used,
                validation_report=validation_report,
                error="Validation failed after bounded retry budget.",
            )

        self._run_node(self.assemble_node, {})
        gate_result = self._run_node(self.gate_node, {})
        if gate_result.status not in (StepStatus.COMPLETED, StepStatus.APPROVED):
            return self._result(
                status="blocked_at_gate",
                attempts_used=attempts_used,
                validation_report=validation_report,
                error="Mailbox owner gate did not approve the review artifact.",
            )
        self._run_node(self.publish_node, {})

        return self._result(
            status="published_review_artifact",
            attempts_used=attempts_used,
            validation_report=validation_report,
        )

    def _register_nodes(self) -> None:
        if not self._registered:
            self.runtime.register(
                self.ingest_node,
                self.plan_node,
                self.workers_node,
                self.validate_node,
                self.assemble_node,
                self.gate_node,
                self.publish_node,
            )
            self._registered = True

    def _run_node(self, node: RuntimeNode, inputs: Dict[str, Any]) -> Any:
        result = self.runtime.run(step=node, inputs=inputs, cost=5.0)
        if result.status == StepStatus.FAILED:
            raise RuntimeError(f"Graph node {node.node_id} failed: {result.error}")
        return result

    def _ingest(self, query: str, max_results: int) -> Dict[str, Any]:
        inbox_resp = self.connector.read("inbox", query=query, max_results=max_results)
        contacts_resp = self.connector.read("contacts")
        calendar_resp = self.connector.read("calendar", max_results=10)
        self.state["threads"] = inbox_resp.items
        self.state["contacts"] = contacts_resp.items
        self.state["calendar"] = calendar_resp.items
        self.state["source_backend"] = inbox_resp.source_backend
        return {
            "threads": inbox_resp.item_count,
            "contacts": contacts_resp.item_count,
            "calendar_events": calendar_resp.item_count,
            "source_backend": inbox_resp.source_backend,
        }

    def _plan(self, case_name: str) -> Dict[str, Any]:
        plan = PlanningSkill().plan(
            PlanSkillInput(
                case_name=case_name,
                time_window="current connector query",
                scope_filter=self.state.get("query", "label:INBOX"),
                priority_sender_categories=["student", "admin"],
                include_draft_replies=True,
                include_action_item_extraction=True,
                include_calendar_sync=True,
                standard_template_focus="standard_faculty_response",
                custom_rules=["Never send without mailbox owner approval", "Bound validation retries"],
            )
        )
        self.state["plan"] = plan
        return {"plan_id": plan.plan_id, "locked": plan.locked, "steps": len(plan.steps)}

    def _workers(self, attempt: int) -> Dict[str, Any]:
        threads: List[EmailThread] = self.state["threads"]
        contacts: List[Dict[str, Any]] = self.state["contacts"]
        metrics = UrgencyDomainCalculatorTool().compute(threads, contacts)
        if not metrics.valid:
            raise ValueError(f"Domain metrics invalid: {metrics.validation_notes}")

        items = self._build_triaged_items(threads, contacts, metrics.per_thread_scores)
        should_inject = (
            self.state.get("inject_validation_failure_once")
            and not self.state.get("failure_injected")
            and attempt == 1
            and items
        )
        if should_inject:
            items[0].draft_reply = None
            self.state["failure_injected"] = True

        inbox = TriagedInbox(
            run_id=f"lab07_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            items=items,
            version=1,
            status=ApprovalStatus.DRAFT,
        )
        self.state["triaged_inbox"] = inbox
        self.state["specialist_registry_summary"] = self._specialist_registry_summary(threads)
        return {
            "attempt": attempt,
            "items": len(items),
            "drafts": sum(1 for item in items if item.draft_reply),
            "injected_failure": should_inject,
            "specialist_registry_summary": self.state["specialist_registry_summary"],
        }

    def _validate(self, attempt: int) -> Dict[str, Any]:
        inbox: TriagedInbox = self.state["triaged_inbox"]
        errors: List[str] = []

        if not inbox.items:
            errors.append("Triaged inbox contains no items.")

        for item in inbox.items:
            if item.draft_status_note == "No reply needed — informational":
                continue
            if item.category != SenderCategory.VENDOR and item.draft_reply is None:
                errors.append(f"Missing draft reply for actionable non-vendor thread {item.thread_id}.")
            for action in item.action_items:
                if action.confirmed:
                    errors.append(f"Action item {action.item_id} is incorrectly marked complete.")
            if item.meeting_request and item.meeting_request.confirmed_by_faculty:
                errors.append(f"Meeting request {item.meeting_request.request_id} was confirmed without approval.")

        if self.state.get("force_validation_failure"):
            errors.append("Forced validation failure for bounded retry demonstration.")

        report = ValidationReport(
            passed=not errors,
            attempt=attempt,
            errors=errors,
            item_count=len(inbox.items),
            draft_count=sum(1 for item in inbox.items if item.draft_reply),
        )
        self.state["validation_report"] = report
        return report.model_dump()

    def _assemble(self) -> Dict[str, Any]:
        inbox: TriagedInbox = self.state["triaged_inbox"]
        template = TemplateSpec(
            template_name="Lab 7 Assembly Preview",
            output_format="markdown",
            header_title="Lab 7 Triaged Inbox with Draft Replies",
        )
        doc = FormattingSkill().format_triaged(inbox, template)
        self.state["formatted_doc"] = doc
        return {"document_id": doc.document_id, "panels": list(doc.panels.keys()), "items": doc.item_count}

    def _gate_summary(self) -> Dict[str, Any]:
        inbox: TriagedInbox = self.state["triaged_inbox"]
        return {
            "pending_review_items": len(inbox.items),
            "draft_replies": sum(1 for item in inbox.items if item.draft_reply),
            "human_gate": "mailbox owner approval required before any send",
        }

    def _publish(self) -> Dict[str, Any]:
        inbox: TriagedInbox = self.state["triaged_inbox"]
        inbox.status = ApprovalStatus.PENDING_REVIEW
        self.state["triaged_inbox"] = inbox
        return {
            "published_artifact": inbox.run_id,
            "status": inbox.status.value,
            "note": "Published to mailbox-owner review queue only; no email sent.",
        }

    def _build_triaged_items(
        self,
        threads: List[EmailThread],
        contacts: List[Dict[str, Any]],
        per_thread_scores: Dict[str, int],
    ) -> List[TriagedEmail]:
        contact_map = {c["contact"].lower(): c for c in contacts}
        items: List[TriagedEmail] = []

        for thread in threads:
            category = self._category_for(thread, contact_map)
            score = per_thread_scores.get(thread.thread_id, 20)
            urgency = self._urgency_for(score)
            body = " ".join(message.body for message in thread.messages)
            lower = f"{thread.subject} {thread.snippet} {body}".lower()
            body_preview = self._body_preview(thread, body)

            action_items = self._action_items(thread, lower)
            meeting_request = self._meeting_request(thread, lower)
            should_reply = UrgencyDomainCalculatorTool.should_generate_reply(thread, category)
            draft_status_note = None
            draft_reply = None
            if category != SenderCategory.VENDOR and should_reply:
                draft_reply = self._draft_reply(thread, category, contact_map)
            elif category != SenderCategory.VENDOR:
                draft_status_note = "No reply needed — informational"

            items.append(
                TriagedEmail(
                    thread_id=thread.thread_id,
                    subject=thread.subject,
                    sender=thread.sender,
                    category=category,
                    urgency=urgency,
                    urgency_score=score,
                    rationale=f"Score {score}/100 from typed calculator; category={category.value}.",
                    body_preview=body_preview,
                    action_items=action_items,
                    meeting_request=meeting_request,
                    draft_reply=draft_reply,
                    draft_status_note=draft_status_note,
                    reply_later=urgency in (UrgencyLevel.LOW, UrgencyLevel.MEDIUM),
                    resurface_date="Next scheduled triage cycle" if urgency in (UrgencyLevel.LOW, UrgencyLevel.MEDIUM) else None,
                )
            )

        items.sort(key=lambda item: item.urgency_score, reverse=True)
        return items

    def _body_preview(self, thread: EmailThread, body: str) -> str:
        raw = (thread.snippet or body or thread.subject).strip()
        return " ".join(raw.split())

    def _category_for(self, thread: EmailThread, contact_map: Dict[str, Dict[str, Any]]) -> SenderCategory:
        sender = thread.sender.lower()
        matched = contact_map.get(sender)
        if matched:
            try:
                return SenderCategory(matched.get("category", "other"))
            except ValueError:
                pass

        # Always route through the same configurable institutional classifier used elsewhere.
        category = classify_sender(thread.sender, contact_map)
        if category != SenderCategory.OTHER:
            return category

        if "student" in sender or ("cs" in sender and ".edu" in sender):
            return SenderCategory.STUDENT
        if "sales" in sender or "promo" in sender or "marketing" in sender:
            return SenderCategory.VENDOR
        return SenderCategory.COLLABORATOR

    def _urgency_for(self, score: int) -> UrgencyLevel:
        if score >= 70:
            return UrgencyLevel.URGENT
        if score >= 45:
            return UrgencyLevel.HIGH
        if score >= 20:
            return UrgencyLevel.MEDIUM
        return UrgencyLevel.LOW

    def _action_items(self, thread: EmailThread, lower_text: str) -> List[ActionItem]:
        action_terms = ["deadline", "due", "submit", "sign", "review", "verify", "approval", "today", "tomorrow"]
        if not any(term in lower_text for term in action_terms):
            return []
        deadline = None
        if "today" in lower_text:
            deadline = "Today"
        elif "tomorrow" in lower_text:
            deadline = "Tomorrow"
        elif "friday" in lower_text:
            deadline = "Friday"
        return [
            ActionItem(
                item_id=f"act_{thread.thread_id[:12]}",
                thread_id=thread.thread_id,
                task=f"Review required action for '{thread.subject}'",
                deadline=deadline,
                owner="Faculty Mailbox Owner",
                confirmed=False,
            )
        ]

    def _meeting_request(self, thread: EmailThread, lower_text: str) -> Optional[MeetingRequest]:
        if not any(term in lower_text for term in ["meeting", "meet", "schedule", "office hours", "slot"]):
            return None
        return MeetingRequest(
            request_id=f"mtg_{thread.thread_id[:12]}",
            thread_id=thread.thread_id,
            sender=thread.sender,
            subject=thread.subject,
            proposed_slots=["Check calendar availability before confirming"],
            confirmed_by_faculty=False,
        )

    def _specialist_draft_for_thread(self, thread: EmailThread) -> Optional[DraftReply]:
        payload = {
            "sender": thread.sender,
            "subject": thread.subject,
            "body": " ".join(message.body for message in thread.messages),
        }
        for domain_name in registry.domains():
            specialist = registry.get(domain_name)
            if not specialist.detect(payload):
                continue
            try:
                output = GenerationAgent(registry).use(specialist, payload)
            except Exception:
                continue
            return DraftReply(
                draft_id=f"drf_{thread.thread_id[:12]}_{domain_name}",
                thread_id=thread.thread_id,
                recipient=thread.sender,
                subject=f"Re: {thread.subject}",
                body=output.body,
                template_used=output.template_name,
                citations=[f"Thread {thread.thread_id}", f"Live specialist route: {domain_name}"],
                status=ApprovalStatus.DRAFT,
                approved_by=None,
            )
        return None

    def _specialist_registry_summary(self, threads: List[EmailThread]) -> Dict[str, Any]:
        checked_live_items = 0
        matched_domains: List[str] = []
        matched_thread_ids: List[str] = []

        for thread in threads:
            checked_live_items += 1
            matched = self._specialist_draft_for_thread(thread)
            if matched is not None:
                matched_thread_ids.append(thread.thread_id)
                if matched.template_used:
                    matched_domains.append(matched.template_used)

        return {
            "checked_live_items": checked_live_items,
            "matched_specialist_items": len(matched_thread_ids),
            "matched_domains": matched_domains,
            "matched_thread_ids": matched_thread_ids,
            "note": f"checked {checked_live_items} live items against specialist registry, {len(matched_thread_ids)} matched this run",
        }

    def _draft_reply(
        self,
        thread: EmailThread,
        category: SenderCategory,
        contact_map: Dict[str, Dict[str, Any]],
    ) -> DraftReply:
        specialist_draft = self._specialist_draft_for_thread(thread)
        if specialist_draft is not None:
            return specialist_draft

        matched = contact_map.get(thread.sender.lower())
        template = (matched or {}).get("standard_template") or f"{category.value}_standard_response"
        salutation = thread.sender.split("@")[0].replace(".", " ").replace("_", " ").title()
        body = (
            f"Dear {salutation},\n\n"
            f"Thank you for your message regarding '{thread.subject}'. I have reviewed the thread "
            "and will follow up on the relevant action items after checking the supporting context.\n\n"
            "Best regards,\nFaculty Mailbox Owner"
        )
        return DraftReply(
            draft_id=f"drf_{thread.thread_id[:12]}",
            thread_id=thread.thread_id,
            recipient=thread.sender,
            subject=f"Re: {thread.subject}",
            body=body,
            template_used=template,
            citations=[f"Thread {thread.thread_id}", f"Sender {thread.sender}"],
            status=ApprovalStatus.DRAFT,
            approved_by=None,
        )

    def _result(
        self,
        status: str,
        attempts_used: int,
        validation_report: Optional[ValidationReport],
        error: Optional[str] = None,
    ) -> GraphRunResult:
        doc = self.state.get("formatted_doc")
        return GraphRunResult(
            run_id=self.runtime.run_id,
            status=status,
            triaged_inbox=self.state.get("triaged_inbox"),
            validation_report=validation_report,
            attempts_used=attempts_used,
            max_retries=self.max_retries,
            retry_events=self.retry_events,
            graph_trace=self.runtime.step_summary(),
            formatted_preview=(doc.rendered_content[:1200] if doc else None),
            source_backend=self.state.get("source_backend", "unknown"),
            specialist_registry_summary=self.state.get("specialist_registry_summary", {}),
            error=error,
        )


def run_lab07_graph(**kwargs: Any) -> GraphRunResult:
    """Convenience function for demos and the Streamlit dashboard."""
    graph = AgenticNodeGraph(max_retries=kwargs.pop("max_retries", 2))
    return graph.run(**kwargs)
