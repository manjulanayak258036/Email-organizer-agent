"""Lab 13 discipline-specific specialists for the email organizer agent."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field


class SpecialistOutput(BaseModel):
    domain: str
    specialist_name: str
    template_name: str
    body: str
    company: Optional[str] = None
    batch: Optional[str] = None
    proposed_slot: Optional[str] = None
    requires_faculty_approval: bool = False
    checklist: List[str] = Field(default_factory=list)
    validation: Dict[str, Any] = Field(default_factory=dict)


class DomainSpecialist:
    domain: str = "generic"

    def detect(self, item: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def generate(self, item: Dict[str, Any]) -> SpecialistOutput:
        raise NotImplementedError

    def validate(self, output: SpecialistOutput) -> bool:
        raise NotImplementedError


class GenerationAgent:
    """Matches the Chapter 3 pseudocode: specialist = registry.get(domain); out = specialist.generate(item)"""

    def __init__(self, registry: Any):
        self.registry = registry

    def use(self, specialist: DomainSpecialist, item: Dict[str, Any]) -> SpecialistOutput:
        if not specialist.detect(item):
            raise ValueError(f"Specialist '{specialist.domain}' does not match the input item.")
        output = specialist.generate(item)
        if not specialist.validate(output):
            raise ValueError(f"Specialist '{specialist.domain}' generated an invalid output.")
        return output


class PlacementCoordinatorSpecialist(DomainSpecialist):
    """Handles placement/recruitment coordination threads from admin placement officers."""

    domain = "placement_coordinator"

    def _extract_company(self, item: Dict[str, Any]) -> str:
        source = f"{item.get('subject', '')} {item.get('body', '')}"
        for pattern in [
            r'"([A-Za-z0-9&.-]+)"',
            r"\b([A-Z]{2,12})\s+for\s+\d{4}\s+batch\b",
            r"\b([A-Z]{2,12})\s+batch\b",
            r"\b([A-Z]{2,12})\s+for\s+HR\b",
            r"\b([A-Z]{2,12})\s+registration\b",
        ]:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value.lower() not in {"the", "this", "for", "hr", "registration"}:
                    return value
        if "placement_officer" in (item.get("sender") or "").lower():
            return "Placement Partner"
        return "Placement Company"

    def _extract_batch(self, item: Dict[str, Any]) -> str:
        source = f"{item.get('subject', '')} {item.get('body', '')}"
        for pattern in [
            r"(\d{4}\s+batch)",
            r"(batch\s+\d{4})",
            r"(for\s+the\s+\d{4}\s+batch)",
            r"(current\s+batch)",
        ]:
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "current batch"

    def detect(self, item: Dict[str, Any]) -> bool:
        sender = (item.get("sender") or "").lower()
        subject = (item.get("subject") or "").lower()
        body = (item.get("body") or "").lower()
        signals = [
            "placement_officer",
            "placement officer",
            "final list",
            "registration link",
            "for hr",
            "hr today",
            "batch",
            "registration list",
        ]
        admin_like = "placement" in sender or "placement" in subject or "placement" in body
        return admin_like and any(token in subject or token in body for token in signals)

    def generate(self, item: Dict[str, Any]) -> SpecialistOutput:
        company = self._extract_company(item)
        batch = self._extract_batch(item)
        body = (
            f"Thank you for the {company} update for the {batch}. Noted, I will coordinate with the department and "
            "route the final list to the relevant contacts. I have recorded the company/batch details and will ensure "
            "the registration list and HR follow-up are aligned with the department's next steps."
        )
        return SpecialistOutput(
            domain=self.domain,
            specialist_name="PlacementCoordinatorSpecialist",
            template_name="placement_coordination_response",
            body=body,
            company=company,
            batch=batch,
            requires_faculty_approval=False,
            checklist=[
                "company_or_batch_reference",
                "coordination_action_present",
                "not_generic_admin_template",
            ],
            validation={"template_name": "placement_coordination_response"},
        )

    def validate(self, output: SpecialistOutput) -> bool:
        if output.template_name == "admin_standard_response":
            return False
        if output.company and output.company.lower() not in output.body.lower():
            return False
        if output.batch and output.batch.lower() not in output.body.lower():
            return False
        if "noted, i will coordinate with the department" not in output.body.lower():
            return False
        return True


class SchedulingCoordinatorSpecialist(DomainSpecialist):
    """Handles meeting and scheduling requests, including seminar and office-hours coordination."""

    domain = "scheduling_coordinator"

    def _extract_slot(self, item: Dict[str, Any]) -> str:
        text = f"{item.get('subject', '')} {item.get('body', '')}"
        patterns = [
            r"(Wednesday\s+at\s+\d{1,2}:\d{2}\s*(?:AM|PM))",
            r"(Thursday\s+at\s+\d{1,2}:\d{2}\s*(?:AM|PM))",
            r"(office\s+hours\s+at\s+\d{1,2}:\d{2}\s*(?:AM|PM))",
            r"(GATE\s+Seminar\s+-\s+.*?\d{1,2}:\d{2}\s*(?:AM|PM))",
            r"(\d{1,2}:\d{2}\s*(?:AM|PM)\s+on\s+Wednesday)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return "a suitable calendar slot"

    def detect(self, item: Dict[str, Any]) -> bool:
        sender = (item.get("sender") or "").lower()
        subject = (item.get("subject") or "").lower()
        body = (item.get("body") or "").lower()
        meeting_terms = [
            "meet during",
            "office hours",
            "schedule",
            "seminar",
            "talk",
            "available",
            "slot",
            "agenda",
        ]
        return any(term in subject or term in body for term in meeting_terms) and (
            "office hours" in subject or "office hours" in body or "seminar" in subject or "seminar" in body
        )

    def generate(self, item: Dict[str, Any]) -> SpecialistOutput:
        proposed_slot = self._extract_slot(item)
        body = (
            f"Thank you for the scheduling request. I will check my calendar availability and coordinate a suitable slot for {proposed_slot}. "
            "I am not confirming the meeting yet; faculty approval is required before the final time is locked in."
        )
        return SpecialistOutput(
            domain=self.domain,
            specialist_name="SchedulingCoordinatorSpecialist",
            template_name="scheduling_coordination_response",
            body=body,
            proposed_slot=proposed_slot,
            requires_faculty_approval=True,
            checklist=[
                "proposed_or_requested_slot",
                "calendar_availability_check",
                "faculty_approval_required",
            ],
            validation={"requires_faculty_approval": True},
        )

    def validate(self, output: SpecialistOutput) -> bool:
        if not output.proposed_slot:
            return False
        if output.proposed_slot.lower() not in output.body.lower():
            return False
        if "check my calendar" not in output.body.lower():
            return False
        if "faculty approval" not in output.body.lower():
            return False
        if "not confirming the meeting yet" not in output.body.lower():
            return False
        return True
