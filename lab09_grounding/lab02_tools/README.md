# Lab 2: Tool-Using Agent — Call Data & Compute

## Goal
Equip the agent with typed tools to read real environment data and perform deterministic domain computations, rather than hallucinating facts or asserting counts from memory/prompts.

## What It Adds
1. **`InboxReaderTool`**: Queries email threads via official Gmail API (`google-api-python-client` with OAuth2) and provides benchmark faculty test fixtures.
2. **`ContactsPriorRepliesTool`**: Resolves contact identities and past reply histories to categorize correspondents into canonical roles (student, admin, collaborator, vendor, other).
3. **`UrgencyDomainCalculatorTool`**: A deterministic domain checker that computes urgency scores, deadline flags, and action item indicators, returning `ComputedDomainMetrics` with a validation boolean `v.valid`.
4. **`ToolUsingCoordinatorAgent`**: Implements the exact Chapter 3 pseudocode:
   ```python
   a = tool.read('the inbox & threads')
   b = tool.read('contacts & prior replies')
   v = tool.compute(a, b)
   assert v.valid
   ```

## Acceptance Criteria (Chapter 3 PDF)
> **Acceptance**: Key numbers and lookups always go through tools, never hand-done in the prompt.

## How to Run the Demo
```bash
python lab02_tools/demo_lab02.py
```

## Proof of Acceptance
When running `demo_lab02.py`:
- **Acceptance Test (Deterministic)** runs `UrgencyDomainCalculatorTool` against `SAMPLE_FACULTY_THREADS` and `SAMPLE_CONTACTS_AND_HISTORY`, a fixed faculty fixture known to contain deadlines and action items.
- Hard assertions (`assert v.valid`, deadline count > 0, action item count > 0) run only against the deterministic fixture so the graded acceptance proof is reproducible.
- **Live Connectivity Check (Informational)** separately runs the same tool pipeline against the authenticated Gmail inbox and prints thread count, deadline count, action count, and validity.
- The live check asserts only that the call succeeds and produces an internally valid result; it intentionally does **not** assert particular live mailbox contents because real inbox state changes day to day.
- All scores, category distributions, deadline counts, and tier breakdowns are computed via `UrgencyDomainCalculatorTool`; no counts are hand-done in prompt text or hardcoded in the coordinator agent.
