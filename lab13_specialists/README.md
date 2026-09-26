# Lab 13: Discipline-Specific Agents

This lab adds a registry-based specialist pattern for domain-specific email handling.

## Specialist registry pattern

The Chapter 3 pseudocode is implemented as:

```python
specialist = registry.get(domain)
out = specialist.generate(item)
GenerationAgent.use(specialist)
```

## Included specialists

- `PlacementCoordinatorSpecialist`: detects placement/recruitment coordination email patterns and produces a placement-specific draft response.
- `SchedulingCoordinatorSpecialist`: detects meeting and seminar scheduling requests and requires explicit faculty approval before finalizing any slot.

## Checkable output schemes

Each specialist enforces a domain-specific schema:

- Placement specialist output must reference the company or batch, include an action phrase like "Noted, I will coordinate with the department", and must not fall back to the generic admin acknowledgement template.
- Scheduling specialist output must include a proposed or requested time slot, a calendar-check note, and must explicitly state that faculty approval is required before final confirmation.

## Run

```bash
python lab13_specialists/demo_lab13.py
```
