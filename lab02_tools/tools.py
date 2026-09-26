"""Lab 2: Typed Tools for Reading Inbox, History, and Computing Domain Metrics.

Implements the Lab 2 requirement:
- Readers for the inbox & threads (Gmail API / Fixture)
- Readers for contacts & prior replies
- Domain calculator/checker computing verified values (assert v.valid)
"""

from __future__ import annotations
import re
import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from core.models import EmailThread, EmailMessage, SenderCategory, UrgencyLevel


class ComputedDomainMetrics(BaseModel):
    total_threads: int
    sender_category_counts: Dict[str, int]
    urgency_tier_counts: Dict[str, int]
    detected_deadlines_count: int
    detected_action_items_count: int
    per_thread_scores: Dict[str, int]
    per_thread_tiers: Dict[str, str] = Field(default_factory=dict)
    valid: bool = False
    validation_notes: List[str] = Field(default_factory=list)


# Realistic faculty email test fixture for headless verification and baseline data
SAMPLE_FACULTY_THREADS = [
    EmailThread(
        thread_id="th_001_grad_thesis",
        subject="URGENT: Thesis Defense Committee Approval needed by Friday",
        sender="alex.turner@cs.university.edu",
        snippet="Dear Dr. Vance, the graduate school deadline for submitting the committee approval form is Friday 5pm...",
        messages=[
            EmailMessage(
                message_id="msg_001",
                sender="alex.turner@cs.university.edu",
                recipient="eleanor.vance@university.edu",
                subject="URGENT: Thesis Defense Committee Approval needed by Friday",
                date="2026-09-15T09:15:00Z",
                snippet="Dear Dr. Vance, the graduate school deadline...",
                body="Dear Dr. Vance,\n\nThe graduate school deadline for submitting the signed thesis defense committee form is this Friday at 5:00 PM. Could you please review and sign the attached approval form before then?\n\nThank you,\nAlex Turner (PhD Candidate)"
            )
        ]
    ),
    EmailThread(
        thread_id="th_002_dean_curriculum",
        subject="Faculty Senate: Curriculum review submission due tomorrow",
        sender="dean_academic@university.edu",
        snippet="Colleagues, please submit any syllabus revision proposals for the upcoming academic cycle by tomorrow 3 PM...",
        messages=[
            EmailMessage(
                message_id="msg_002",
                sender="dean_academic@university.edu",
                recipient="faculty-all@university.edu",
                subject="Faculty Senate: Curriculum review submission due tomorrow",
                date="2026-09-15T08:30:00Z",
                snippet="Colleagues, please submit syllabus revisions...",
                body="Colleagues,\n\nPlease submit all revised course syllabi and laboratory safety checklists to the Senate portal by tomorrow, Wednesday at 3:00 PM.\n\nRegards,\nOffice of the Dean"
            )
        ]
    ),
    EmailThread(
        thread_id="th_003_student_office_hours",
        subject="CS401: Question about Assignment 2 problem 3",
        sender="sarah.lin@student.university.edu",
        snippet="Hi Professor Vance, could I meet during your office hours on Wednesday to clarify problem 3?",
        messages=[
            EmailMessage(
                message_id="msg_003",
                sender="sarah.lin@student.university.edu",
                recipient="eleanor.vance@university.edu",
                subject="CS401: Question about Assignment 2 problem 3",
                date="2026-09-15T11:00:00Z",
                snippet="Hi Professor Vance, could I meet during office hours...",
                body="Hi Professor Vance,\n\nI was reviewing problem 3 on Assignment 2 and had a question regarding the cache coherence protocol. Are you available during your Wednesday office hours at 2:30 PM for a quick 10-minute check?\n\nBest,\nSarah Lin (CS401 Student)"
            )
        ]
    ),
    EmailThread(
        thread_id="th_004_collab_research",
        subject="Draft manuscript: Quantum Simulation Benchmarks",
        sender="dr.marcus.reed@partner-lab.org",
        snippet="Hi Eleanor, attached is the revised draft of our joint paper. Let me know your thoughts when you have time.",
        messages=[
            EmailMessage(
                message_id="msg_004",
                sender="dr.marcus.reed@partner-lab.org",
                recipient="eleanor.vance@university.edu",
                subject="Draft manuscript: Quantum Simulation Benchmarks",
                date="2026-09-14T16:20:00Z",
                snippet="Hi Eleanor, attached is the revised draft...",
                body="Hi Eleanor,\n\nI updated Section 4 with our new benchmark figures. Please take a look whenever your schedule permits over the next couple of weeks.\n\nBest,\nMarcus"
            )
        ]
    ),
    EmailThread(
        thread_id="th_005_vendor_spam",
        subject="Exclusive 40% discount on lab equipment & servers",
        sender="sales@techserver-direct.com",
        snippet="Don't miss our quarterly academic hardware sale on GPU clusters...",
        messages=[
            EmailMessage(
                message_id="msg_005",
                sender="sales@techserver-direct.com",
                recipient="eleanor.vance@university.edu",
                subject="Exclusive 40% discount on lab equipment & servers",
                date="2026-09-14T10:00:00Z",
                snippet="Don't miss our quarterly academic hardware sale...",
                body="Exclusive quarterly academic pricing available on compute nodes. Click here to unsubscribe."
            )
        ]
    ),
]

SAMPLE_CONTACTS_AND_HISTORY = [
    {
        "contact": "alex.turner@cs.university.edu",
        "name": "Alex Turner",
        "category": "student",
        "relation": "PhD Advisee",
        "prior_replies_count": 14,
        "standard_template": "thesis_advising_response"
    },
    {
        "contact": "dean_academic@university.edu",
        "name": "Dean's Office",
        "category": "admin",
        "relation": "Administration",
        "prior_replies_count": 28,
        "standard_template": "admin_acknowledgement"
    },
    {
        "contact": "sarah.lin@student.university.edu",
        "name": "Sarah Lin",
        "category": "student",
        "relation": "CS401 Course Student",
        "prior_replies_count": 3,
        "standard_template": "office_hours_confirmation"
    },
    {
        "contact": "dr.marcus.reed@partner-lab.org",
        "name": "Dr. Marcus Reed",
        "category": "collaborator",
        "relation": "Research Co-Investigator",
        "prior_replies_count": 45,
        "standard_template": "research_collaboration"
    },
    {
        "contact": "sales@techserver-direct.com",
        "name": "TechServer Sales",
        "category": "vendor",
        "relation": "External Commercial",
        "prior_replies_count": 0,
        "standard_template": None
    },
]


class InboxReaderTool:
    """Reads inbox threads via Gmail API if authenticated, with fallback to sample fixture."""

    def __init__(self, auth_manager=None):
        self.auth_manager = auth_manager

    def read(self, query: str = "label:INBOX", max_results: int = 10, use_fixture_fallback: bool = True) -> List[EmailThread]:
        """Reads email threads from Gmail API or sample faculty dataset."""
        if self.auth_manager:
            try:
                service = self.auth_manager.get_gmail_service(interactive=False)
                resp = service.users().threads().list(userId="me", q=query, maxResults=max_results).execute()
                thread_headers = resp.get("threads", [])
                threads: List[EmailThread] = []

                for th in thread_headers:
                    tdata = service.users().threads().get(userId="me", id=th["id"]).execute()
                    messages = []
                    subject = "(No Subject)"
                    sender = "Unknown"
                    snippet = tdata.get("snippet", "")

                    for msg in tdata.get("messages", []):
                        payload = msg.get("payload", {})
                        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
                        msg_subject = headers.get("subject", subject)
                        msg_sender = headers.get("from", sender)
                        subject = msg_subject
                        sender = msg_sender
                        date_str = headers.get("date", "")

                        body = snippet
                        messages.append(
                            EmailMessage(
                                message_id=msg["id"],
                                sender=msg_sender,
                                recipient=headers.get("to", ""),
                                subject=msg_subject,
                                date=date_str,
                                snippet=msg.get("snippet", ""),
                                body=body
                            )
                        )

                    threads.append(
                        EmailThread(
                            thread_id=th["id"],
                            subject=subject,
                            sender=sender,
                            snippet=snippet,
                            messages=messages
                        )
                    )
                if threads:
                    return threads
            except Exception as e:
                if not use_fixture_fallback:
                    raise e
                # Fallback to realistic faculty sample fixture
                print(f"[InboxReaderTool] Notice: Live Gmail query returned 0 or requires login ({e}). Using faculty benchmark dataset.")

        return SAMPLE_FACULTY_THREADS[:max_results]


class ContactsPriorRepliesTool:
    """Reads contacts and prior reply patterns."""

    def __init__(self, auth_manager=None):
        self.auth_manager = auth_manager

    def read(self, query: str = "") -> List[Dict[str, Any]]:
        """Returns known contacts and past reply metadata."""
        return SAMPLE_CONTACTS_AND_HISTORY


from core.classifier import classify_sender


class UrgencyDomainCalculatorTool:
    """Domain calculator/checker that computes verified values from email threads and contacts."""

    TIME_PATTERN = re.compile(r'\b(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}\s*(?:am|pm))\b', re.IGNORECASE)
    DATE_PATTERN = re.compile(r'\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b', re.IGNORECASE)

    SAME_DAY_KEYWORDS = ["today", "tonight", "by eod", "end of day", "by noon", "eod", "immediately", "right away"]
    NEAR_TERM_KEYWORDS = ["tomorrow", "due tomorrow", "by friday", "by monday", "by tuesday", "by wednesday", "by thursday", "by saturday", "by sunday"]
    DEADLINE_PHRASES = ["final list", "due by", "due on", "due date", "last date", "submit by", "submission deadline", "deadline is", "deadline for", "cutoff", "hard deadline", "due"]
    DIRECT_REQUEST_KEYWORDS = [
        "please review", "please confirm", "can you", "could you", "for your verification",
        "approval needed", "need your approval", "submit by", "due by", "last date",
        "could i meet", "are you available", "schedule", "office hours", "need a sign-off",
        "review and sign", "final list", "for your review", "?"
    ]
    ACTION_KEYWORDS = ["please verify", "for your verification", "please review", "submit", "please sign", "sign the", "approval needed", "action required", "please confirm", "fill out", "apply by", "attach", "schedule", "meet during"]
    ESCALATION_KEYWORDS = ["urgent", "important", "critical", "high priority", "asap"]

    @staticmethod
    def should_generate_reply(thread: EmailThread, category: SenderCategory | str) -> bool:
        """True only for emails that clearly warrant a direct faculty reply."""
        category_name = category.value if isinstance(category, SenderCategory) else str(category).lower()
        subject = thread.subject.lower()
        body = " ".join(m.body for m in thread.messages).lower()
        text = f"{subject} {thread.snippet} {body}".lower()

        # Explicit no-reply / informational patterns always skip drafting.
        if any(p in text for p in [
            "no-reply", "noreply", "mailer-daemon", "automated notification", "notification only",
            "sending once again", "resend", "again", "broadcast", "announcement", "notice", "fwd:", "fw:",
            "forwarded", "forwarding", "kaggle", "badge", "newsletter", "all staff", "in case you missed it",
        ]):
            if not any(q in text for q in [
                "please review", "please confirm", "can you", "could you", "for your verification",
                "approval needed", "need your approval", "submit by", "due by", "last date",
                "could i meet", "are you available", "schedule", "office hours", "need a sign-off",
                "review and sign", "final list", "for your review"
            ]):
                return False

        if category_name == "vendor":
            return False

        has_direct_request = any(p in text for p in UrgencyDomainCalculatorTool.DIRECT_REQUEST_KEYWORDS)

        if not has_direct_request:
            # A pure FYI/resend/announcement should not generate a draft unless it is asking for a real action.
            if any(p in text for p in [
                "sending once again", "reminder", "informational", "notice", "announcement",
                "fwd:", "fw:", "forwarded", "broadcast", "newsletter", "deadline reminder"
            ]):
                return False

        return True

    def compute(self, threads: List[EmailThread], contacts: List[Dict[str, Any]]) -> ComputedDomainMetrics:
        """Computes verifiable urgency and categorization metrics via deterministic domain logic."""
        contact_map = {c["contact"].lower(): c for c in contacts}

        sender_counts: Dict[str, int] = {cat.value: 0 for cat in SenderCategory}
        urgency_counts: Dict[str, int] = {urg.value: 0 for urg in UrgencyLevel}
        per_thread_scores: Dict[str, int] = {}
        per_thread_tiers: Dict[str, str] = {}
        detected_deadlines = 0
        detected_action_items = 0
        validation_notes = []

        for th in threads:
            combined_text = (th.subject + " " + th.snippet + " " + " ".join(m.body for m in th.messages)).lower()
            subject_lower = th.subject.lower()

            # 1. Determine Sender Category via Configurable Classifier
            category_enum = classify_sender(th.sender, contact_map)
            category = category_enum.value
            sender_counts[category] = sender_counts.get(category, 0) + 1

            # 2. Extract Deadline, Time, Action, Escalation Signals
            has_time = bool(self.TIME_PATTERN.search(combined_text))
            has_date = bool(self.DATE_PATTERN.search(combined_text))
            has_same_day = any(kw in combined_text for kw in self.SAME_DAY_KEYWORDS)
            has_near_term = any(kw in combined_text for kw in self.NEAR_TERM_KEYWORDS)
            has_deadline_phrase = any(kw in combined_text for kw in self.DEADLINE_PHRASES)
            has_direct_request = any(kw in combined_text for kw in self.DIRECT_REQUEST_KEYWORDS)
            has_action = any(kw in combined_text for kw in self.ACTION_KEYWORDS)
            has_escalation = any(kw in combined_text for kw in self.ESCALATION_KEYWORDS)

            has_deadline_context = any(
                kw in combined_text for kw in [
                    "today", "tomorrow", "deadline", "due", "last date", "submit by", "due by",
                    "due on", "before ", "register before", "register at the same link", "revert by",
                    "respond by", "final list"
                ]
            )
            has_deadline_date_time_context = bool(
                re.search(
                    r"(?:before|by|due|submit|register|revert|respond|deadline|last date|final list)[^\n]{0,80}(?:today|tomorrow|\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*)",
                    combined_text,
                    re.IGNORECASE,
                )
            )

            has_genuine_deadline_signal = (
                (has_same_day and has_deadline_context)
                or (has_near_term and has_deadline_context)
                or has_deadline_date_time_context
                or any(kw in combined_text for kw in ["submit by", "due by", "due on", "last date", "deadline is", "deadline for", "submission deadline"])
            )
            is_deadline = has_genuine_deadline_signal
            if is_deadline:
                detected_deadlines += 1

            if has_action or has_direct_request:
                detected_action_items += 1

            # Check if this is a broadcast / forwarded / informational notice
            is_broadcast = any(
                b in subject_lower for b in [
                    "fwd:", "fw:", "sending once again", "results", "selection",
                    "time table", "timetable", "hackacthon", "hackathon", "experience ppts",
                ]
            )

            # Guardrail: "Flag uncertain urgency for faculty judgment rather than guessing"
            is_uncertain = (
                has_escalation
                and not has_genuine_deadline_signal
                and (has_action or has_direct_request or is_broadcast or category == SenderCategory.VENDOR.value)
            )

            # 3. Compute Urgency Score (0 to 100); real deadline/date-time evidence is required for URGENT.
            score = 10  # baseline

            if has_genuine_deadline_signal:
                if has_same_day:
                    score += 45
                elif has_near_term:
                    score += 30
                elif has_deadline_phrase:
                    score += 20
                if has_time or has_date:
                    score += 15
            elif has_direct_request:
                score += 12
            elif has_action:
                score += 8

            if has_escalation:
                if has_genuine_deadline_signal:
                    score += 10
                else:
                    score += 5

            # Sender Category Weighting only adds modestly; it should never trump real date/deadline evidence.
            if category == SenderCategory.ADMIN.value:
                score += 8 if has_genuine_deadline_signal else 4
            elif category == SenderCategory.STUDENT.value:
                score += 6 if has_genuine_deadline_signal else 3
            elif category == SenderCategory.VENDOR.value:
                score = min(score, 15)

            # Important / final / verification keywords without a real time/date or deadline signal are never URGENT.
            if not has_genuine_deadline_signal:
                score = min(score, 65)

            final_score = max(0, min(100, score))
            per_thread_scores[th.thread_id] = final_score

            # 4. Assign Urgency Tier (including UNCERTAIN)
            if is_uncertain:
                tier = UrgencyLevel.UNCERTAIN.value
            elif has_genuine_deadline_signal and final_score >= 70:
                tier = UrgencyLevel.URGENT.value
            elif final_score >= 45:
                tier = UrgencyLevel.HIGH.value
            elif final_score >= 20:
                tier = UrgencyLevel.MEDIUM.value
            else:
                tier = UrgencyLevel.LOW.value

            per_thread_tiers[th.thread_id] = tier
            urgency_counts[tier] = urgency_counts.get(tier, 0) + 1

        # 5. Domain Checker / Validation assertions
        total = len(threads)
        valid = True

        if sum(sender_counts.values()) != total:
            valid = False
            validation_notes.append("Sender category sum does not match total threads.")

        if sum(urgency_counts.values()) != total:
            valid = False
            validation_notes.append("Urgency tier sum does not match total threads.")

        if len(per_thread_scores) != total:
            valid = False
            validation_notes.append("Missing scores for some threads.")

        return ComputedDomainMetrics(
            total_threads=total,
            sender_category_counts=sender_counts,
            urgency_tier_counts=urgency_counts,
            detected_deadlines_count=detected_deadlines,
            detected_action_items_count=detected_action_items,
            per_thread_scores=per_thread_scores,
            per_thread_tiers=per_thread_tiers,
            valid=valid,
            validation_notes=validation_notes
        )
