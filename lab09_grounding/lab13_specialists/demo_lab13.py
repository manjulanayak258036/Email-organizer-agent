"""Lab 13 acceptance demo: two domain specialists with schema validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab13_specialists.registry import registry
from lab13_specialists.specialists import GenerationAgent


def generic_reply(item: dict) -> str:
    return (
        "Thank you for your message. I have noted the details and will review this when available. "
        "Please let me know if there is anything urgent or time-sensitive."
    )


def main() -> None:
    print("=" * 80)
    print("LAB 13: Discipline-Specific Agents - Domain Specialisation")
    print("=" * 80)
    print("Command to run: python lab13_specialists/demo_lab13.py")

    placement_item = {
        "sender": "Placement Officer <placement_officer@kletech.ac.in>",
        "subject": '"LTM" for 2027 batch --- Final list to be sent to HR today (22nd September) at 3:00 pm',
        "body": (
            "Dear Professor, the final list for the 2027 batch has to be sent to HR today at 3:00 PM. "
            "Please coordinate with the department and keep the registration list aligned with the LTM placement process."
        ),
    }

    scheduling_item = {
        "sender": "Seminar Coordinator <gate@university.edu>",
        "subject": "GATE Seminar - Wednesday 3:00 PM room 214",
        "body": (
            "Dear Professor, I would like to schedule the GATE seminar during your office hours. "
            "Are you available on Wednesday at 3:00 PM or Thursday at 11:00 AM for a brief talk?"
        ),
    }

    print("\n-- Generic fallback reply (for contrast) --")
    print(generic_reply(placement_item))

    print("\n-- Placement specialist --")
    placement_agent = GenerationAgent(registry)
    placement_specialist = registry.get("placement_coordinator")
    placement_output = placement_agent.use(placement_specialist, placement_item)
    print(placement_output.model_dump())
    print(f"Placement schema valid: {placement_specialist.validate(placement_output)}")
    assert placement_specialist.validate(placement_output)
    assert "LTM" in placement_output.body
    assert "noted, i will coordinate with the department" in placement_output.body.lower()
    assert placement_output.template_name != "admin_standard_response"

    print("\n-- Scheduling specialist --")
    scheduling_specialist = registry.get("scheduling_coordinator")
    scheduling_output = placement_agent.use(scheduling_specialist, scheduling_item)
    print(scheduling_output.model_dump())
    print(f"Scheduling schema valid: {scheduling_specialist.validate(scheduling_output)}")
    assert scheduling_specialist.validate(scheduling_output)
    assert scheduling_output.proposed_slot is not None
    assert "calendar" in scheduling_output.body.lower()
    assert "faculty approval" in scheduling_output.body.lower()
    assert "not confirming the meeting yet" in scheduling_output.body.lower()

    print("\n[ACCEPTANCE PASS] Both specialists produced domain-specific, checkable output from real inbox patterns and rejected the generic admin reply template path.")


if __name__ == "__main__":
    main()
