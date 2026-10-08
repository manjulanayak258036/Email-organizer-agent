"""Domain data models for the Email Organizer Agent.

Implements the Canonical Data Model from Chapter 3:
- Sender category (Student, admin, collaborator, vendor, other)
- Urgency signal (Deadlines, escalation language, priority markers)
- Standard response library (Faculty templates for common queries)
- Action-item pattern (Tasks, deadlines, commitments)
- Meeting request signal (Proposed dates/times, scheduling language)
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import datetime


class SenderCategory(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"
    COLLABORATOR = "collaborator"
    VENDOR = "vendor"
    OTHER = "other"


class UrgencyLevel(str, Enum):
    URGENT = "urgent"          # Requires response within 2-4 hours
    HIGH = "high"              # Within 24 hours / hard deadline today
    MEDIUM = "medium"          # Standard response within 2-3 days
    LOW = "low"                # Informational / no immediate deadline
    UNCERTAIN = "uncertain"    # Conflicting or ambiguous signals; flagged for faculty judgment


class ApprovalStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    EDITED = "edited"
    OVERRIDDEN = "overridden"
    REJECTED = "rejected"


class EmailMessage(BaseModel):
    message_id: str
    sender: str
    recipient: str
    subject: str
    date: str
    snippet: str
    body: str


class EmailThread(BaseModel):
    thread_id: str
    subject: str
    sender: str
    snippet: str
    messages: List[EmailMessage] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class ActionItem(BaseModel):
    item_id: str
    thread_id: str
    task: str
    deadline: Optional[str] = None
    owner: str = "Faculty"
    confirmed: bool = False  # Guardrail: Never mark complete without confirmation


class MeetingRequest(BaseModel):
    request_id: str
    thread_id: str
    sender: str
    subject: str
    proposed_slots: List[str] = Field(default_factory=list)
    confirmed_slot: Optional[str] = None
    confirmed_by_faculty: bool = False  # Guardrail: Never confirm meeting time without approval


class DraftReply(BaseModel):
    draft_id: str
    thread_id: str
    recipient: str
    subject: str
    body: str
    template_used: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.DRAFT
    human_edits: Optional[str] = None
    approved_by: Optional[str] = None
    evidence_record: Optional[Dict[str, Any]] = None


class TriagedEmail(BaseModel):
    thread_id: str
    subject: str
    sender: str
    category: SenderCategory
    urgency: UrgencyLevel
    urgency_score: int
    rationale: str
    body_preview: Optional[str] = None
    action_items: List[ActionItem] = Field(default_factory=list)
    meeting_request: Optional[MeetingRequest] = None
    draft_reply: Optional[DraftReply] = None
    draft_status_note: Optional[str] = None
    reply_later: bool = False
    resurface_date: Optional[str] = None


class TriagedInbox(BaseModel):
    run_id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    items: List[TriagedEmail] = Field(default_factory=list)
    version: int = 1
    status: ApprovalStatus = ApprovalStatus.DRAFT


class PlanStep(BaseModel):
    step_id: int
    name: str
    description: str
    status: str = "pending"


class ExecutionPlan(BaseModel):
    plan_id: str
    target_scope: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    steps: List[PlanStep] = Field(default_factory=list)
    locked: bool = False
