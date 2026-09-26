# Email Organizer Agent - Walkthrough (Labs 1-6)

This document tracks the progress, implementation details, and verification outcomes across the 14-lab build for the **Email Organizer Agent Worklet** (Chapter 3).

---

## Lab 1: Agent vs Chatbot - Planner Loop (`lab01_agent_loop/`)

- **Goal**: Implement a deliberate `clarify -> plan -> revise` agent loop rather than a one-shot chatbot.
- **Components**:
  - `CoordinatorPlanner` (`lab01_agent_loop/planner.py`): Checks incoming requests across 4 required dimensions (`time_window`, `urgency_focus`, `draft_templates`, `scope_filter`).
  - Proposes a 6-step `ExecutionPlan` (`core/models.py`).
  - Interactively revises the plan based on human feedback and locks the plan.
- **Acceptance Verification**:
  ```bash
  python lab01_agent_loop/demo_lab01.py
  ```
  - Result: Given a vague prompt, asks at least 2 clarifying questions, yields an editable 6-step plan, incorporates user revisions, and locks the plan. Status: **PASS**.

---

## Lab 2: Tool-Using Agent - Call Data & Compute (`lab02_tools/`)

- **Goal**: Guarantee that lookups and numbers come through typed tools, never asserted or hand-done in prompt context.
- **Components**:
  - `InboxReaderTool`: Interacts with the Gmail API via OAuth2 credentials, falling back to realistic faculty benchmark fixtures (`SAMPLE_FACULTY_THREADS`).
  - `ContactsPriorRepliesTool`: Looks up contact roles (student, admin, collaborator, vendor) and past reply metrics.
  - `UrgencyDomainCalculatorTool`: Computes urgency scores (0-100), urgency tiers (`URGENT`, `HIGH`, `MEDIUM`, `LOW`), deadline counts, and action item indicators. Enforces `assert v.valid`.
  - `ToolUsingCoordinatorAgent`: Executes the Chapter 3 tool pattern:
    ```python
    a = tool.read('the inbox & threads')
    b = tool.read('contacts & prior replies')
    v = tool.compute(a, b)
    assert v.valid
    ```
- **Acceptance Verification**:
  ```bash
  python lab02_tools/demo_lab02.py
  ```
  - Deterministic acceptance path: `SAMPLE_FACULTY_THREADS` fixture data processes 5 threads, detects 2 deadlines and 4 action items, validates category/tier distributions, and enforces `v.valid == True`.
  - Live connectivity path: real Gmail is checked separately through the connector and prints backend, thread count, deadline count, and action count without asserting specific mailbox contents, because live inbox content is non-deterministic. Status: **PASS**.

---

## Lab 3: Skill Creation - Reusable Plan & Format Skills (`lab03_skills/`)

- **Goal**: Package repeatable agent capability into reusable, schema-typed skills activating the **Plan Node** and **Assembly Node**.
- **Components**:
  - `PlanningSkill` (`lab03_skills/skills.py`):
    ```python
    skill plan(inputs: PlanSkillInput) -> ExecutionPlan:
        return expand(inputs).lock()
    ```
    - Inputs: `PlanSkillInput` schema (`case_name`, `time_window`, `scope_filter`, `priority_sender_categories`, `include_draft_replies`, `standard_template_focus`, `custom_rules`).
    - Output: Locked `ExecutionPlan` (`plan.locked = True`).
  - `FormattingSkill` (`lab03_skills/skills.py`):
    ```python
    skill format_triaged(result: TriagedInbox, template: TemplateSpec) -> FormattedDocument
    ```
    - Inputs: `TriagedInbox` and `TemplateSpec` (`output_format`: Markdown, HTML, Text).
    - Renders the Section 3.9 Dashboard Template panels:
      - **Panel 1: Triaged Inbox**: Emails ranked by category and urgency score.
      - **Panel 2: Draft-Reply Queue**: Draft replies with citations and template citations awaiting faculty approval.
      - **Panel 3: Action-Item List**: Tasks and deadlines with `confirmed=False` guardrail.
      - **Panel 4: Follow-up Digest**: "Reply later" items and meeting requests.
  - `SkillUsingCoordinatorAgent` (`lab03_skills/agent.py`): Combines Lab 2 tools with Lab 3 skills.
- **Acceptance Verification**:
  ```bash
  python lab03_skills/demo_lab03.py
  ```
  - Case 1: Teaching & Student Advising Workload.
  - Case 2: Faculty Senate & Research Operations Workload.
  - Result: Both distinct cases execute through the identical skill instances with zero code changes, producing locked plans and 4-panel dashboard documents. Status: **PASS**.

---

## Lab 4: Memory & Retrieval - State vs Stored (`lab04_memory/`)

- **Goal**: Separate short-term run state from long-term stored knowledge, activating the **Retrieval Node** and laying the groundwork for evidence-grounded screening and validation.
- **Components**:
  - `LocalVectorEmbedder` (`lab04_memory/memory.py`): Pure Python TF-IDF embedder and cosine similarity calculator.
  - `SessionState`: Ephemeral run state tracking the active candidate draft (`state.draft = candidate`). Isolated from long-term archives.
  - `LongTermMemoryStore`: Reference policies/syllabi (`store`) and historical email exchanges with past replies (`history`).
  - `MemoryManager`: Enforces the Chapter 3 memory split:
    ```python
    state.draft = candidate
    hits = memory.retrieve(store, tags)
    prior = memory.retrieve(history, embed(candidate), k=5)
    ```
  - `RetrievalAgent` (`lab04_memory/agent.py`): Ties together candidate ingestion, store tag filtering, and historical prior similarity matching.
- **Acceptance Verification**:
  ```bash
  python lab04_memory/demo_lab04.py
  ```
  - Student query retrieves the CS401 office-hours policy and ranks `prior_th_101` as the top similar prior.
  - Senate/dean request retrieves curriculum/deadline policies and ranks `prior_th_103` as the top similar prior.
  - Thesis filing retrieves thesis policy and ranks `prior_th_102` as the top similar prior.
  - Anti-corruption check proves ephemeral draft mutations leave store and history unchanged. Status: **PASS**.

---

## Lab 5: MCP-Style Connector - One Server for All Sources (`lab05_connector/`)

- **Goal**: Route all data access through a single connector so no agent touches Gmail, Calendar, memory, history, or contacts directly.
- **Components**:
  - `MCPStyleConnector` (`lab05_connector/connector.py`): Registers all sources with `connector.expose(...)`.
  - `ConnectorResponse`: Typed envelope declaring `source_name`, `operation`, `item_count`, and `source_backend` (`live_api` or `fixture`).
  - Live Gmail and Google Calendar access through `GoogleAuthManager`, with explicit fixture fallback when live access is unavailable.
  - Memory store, history similarity search, and contacts access exposed through the same `read()` / `search()` interface.
- **Acceptance Verification**:
  ```bash
  python lab05_connector/demo_lab05.py
  ```
  - Result: All five sources (`inbox`, `calendar`, `store`, `history`, `contacts`) are registered; Gmail and Calendar return provenance-labeled live results; memory/history/contact fixture sources are readable/searchable; Labs 2-4 access patterns route through the connector; swapping live vs fixture backend requires zero agent code changes. Status: **PASS**.

---

## Lab 6: Governed Runtime - Skills, Tools, Memory, Audit (`lab06_runtime/`)

- **Goal**: Wrap the Phase-A components in a governed runtime that audits every action, enforces budgets and approval gates, and checkpoints before advancing.
- **Components**:
  - `GovernedRuntime` (`lab06_runtime/runtime.py`): Registers and executes runtime nodes with audit, budget, gate, and checkpoint handling.
  - `RuntimeNode`: Typed wrapper for callable plan/tool/skill/memory/connector steps.
  - `StepResult`: Structured record of inputs, outputs, status, budget, approval state, elapsed time, and errors.
  - `CheckpointStore`: Durable JSONL checkpoints loaded by run ID for crash recovery.
  - `ApprovalGate` and `BudgetTracker`: Human-gate abstraction and total/per-node budget enforcement.
- **Acceptance Verification**:
  ```bash
  python lab06_runtime/demo_lab06.py
  ```
  - Result: Five nodes register and execute; every step is audited with inputs and outputs; every completed step is checkpointed; a second runtime with the same run ID skips completed work; an over-budget step is blocked; the approval-required connector node is approved and recorded. Status: **PASS**.

---

## Part A: Root-Cause Fixes and Real-Inbox Verification

- **Issue diagnosed**: the graph path had drifted away from the canonical classifier, and the urgency scorer was treating non-deadline escalation language as if it were actual time-based urgency. The live inbox confirmed this by surfacing threads that looked important but lacked real deadlines or time evidence.
- **Root-cause fix**: the graph now uses the canonical sender classifier, and urgency scoring only raises `URGENT` when there is concrete date/time or deadline proof in the email body. Generic “important” language or escalation-only phrasing no longer overrides a valid deadline check.
- **Additional gating fix**: informational or broadcast threads are no longer treated as actionable reply candidates when they lack a human-prioritized request or required reply.
- **Verification**: the real 20-thread mailbox review was checked against actual email-body evidence before sign-off. The false-positive “Important points to be noted” case was removed from urgent triage while genuine same-day deadline rows remained clearly urgent.
- **Final DOM confirmation**: the live page check confirms the collapsed Triaged Inbox row renders visible `Urgent` / `Admin` chips and the expanded row contains only sender, subject, and body text with no forbidden metadata labels. The action rows retain exactly one deadline chip per row instead of zero or duplicate labels.

---

## Part B: Dashboard UI Polish and Review Experience

- **Theme update**: the dashboard was restyled to align with the PDF node-graph legend: navy for coordinator/header chrome, light blue for agent-generated panels, amber for approval-waiting items, and green for approved/published state.
- **UX cleanup**: all emoji UI icons were removed from the interface, and each of the five tabs now includes explanatory subheadings that clarify the purpose of the panel.
- **Inbox behavior**: the Gmail-style rows are collapsed by default on fresh page load, with urgency/category chips visible directly on the collapsed row. Only the row header is visible until the user clicks for details.
- **Detail hygiene**: duplicated repeated header lines were removed from expanded Action-Item and Follow-up rows, and the Triaged Inbox expanded panel now shows only sender, subject, and the actual email body content rather than metadata fields.
- **Action tracking**: the Action-Item List includes the required “Mark Confirmed” checkbox, and the Follow-up Digest retains its own review flow without redundant details.
- **Badge legend**: urgency, category, and status badges now use color-coded styling with a visible legend at the top of the dashboard so the faculty owner can interpret the queue quickly.
- **Verification**: the dashboard source compiles successfully, the browser verification confirms the row state and content behavior, and the Lab 8 parallel-swarm handoff is ready.

---

## Lab 8: Parallel Swarm - merge by plan alignment

- **Goal**: process many email threads concurrently and merge the strongest candidate per thread based on alignment with the active review plan.
- **Implementation**: `lab08_parallel_swarm/agent.py` defines a `ParallelSwarmCoordinator` that runs each thread through a worker pool, scores candidate urgency and relevance, then keeps the highest-scoring aligned result for each thread ID.
- **Acceptance**: `python lab08_parallel_swarm/demo_lab08.py` validates the swarm output contains one merged candidate per input thread and maintains a valid average alignment score.
- **Timing evidence**: the accepted run shows the parallel path beating the sequential baseline in repeated checks (`0.0295s vs 0.1547s`, then `0.0279s vs 0.1524s`), while the final merged scores stayed identical across both runs despite different merge-trace ordering. This is evidence of real parallel execution, not a disguised sequential loop.
- **Status**: PASS through the acceptance script and aligned with the Chapter 3 parallel-processing spec.

---

## Lab 9: Deep Research - Ground & Evidence (`lab09_grounding/`)

- **Goal**: ensure every candidate reply or recommendation is grounded in an in-scope source and reject ungrounded outputs before they can reach the mailbox owner.
- **Implementation focus**: the grounding pass validates evidence citations, checks source scope, and eliminates candidates that do not map to actual thread history or institutional policies.
- **Acceptance bar**: every output must map to an in-scope source; any candidate without evidence is rejected rather than silently published.
- **Acceptance Verification**:
  ```bash
  python lab09_grounding/demo_lab09.py
  ```
  - Result: `cand_001` and `cand_002` are accepted as grounded; `cand_003` is rejected as ungrounded.
  - Evidence: the script prints in-scope thread provenance for the two accepted cases and exits cleanly with the acceptance assertions satisfied.
  - Status: **PASS**.

---

## Lab 10: Ops Resilience - Validate, Diagnose, Fix (`lab10_self_healing/`)

- **Goal**: validate each output, diagnose the exact failure mode, repair only the failing part, and keep looping until the run is clean or the retry budget is exhausted.
- **Implementation focus**: a self-healing validation loop checks the current result, explains the failed condition, regenerates the broken segment, and re-runs validation before publishing.
- **Acceptance bar**: the same item may be retried, but the final output must pass validation without silently carrying a broken result.
- **Acceptance Verification**:
  ```bash
  python lab10_self_healing/demo_lab10.py
  ```
  - Result: the validation trace reports the failing candidate, the repair event rebinds it to an in-scope thread, and the final validation passes.
  - Status: **PASS**.

---

## Lab 11: SDLC Factory - Spec → Tested Output (`lab11_sdlc_factory/`)

- **Goal**: treat the plan as a spec and the output as a tested implementation, so nothing advances to the mailbox owner without a fully passing acceptance report.
- **Implementation focus**: build the draft artifact from the locked spec, run the automated acceptance suite, and gate human review on a green report.
- **Acceptance bar**: no triaged inbox with draft replies can pass to the mailbox owner without a passing report.
- **Acceptance Verification**:
  ```bash
  python lab11_sdlc_factory/demo_lab11.py
  ```
  - Result: the artifact built from the locked plan passes all checks and the output records a green acceptance report.
  - Status: **PASS**.

---

## Lab 12: Safety & Governance - Approval, Eval, Rollback (`lab12_governance/`)

- **Goal**: ensure only mailbox-owner-approved outputs publish, capture a release record with metrics, and provide a clean rollback path for prior versions.
- **Implementation focus**: the governance agent enforces a hard approval gate, stores versioned release records, and exposes a deterministic rollback call for a published version.
- **Acceptance bar**: any draft that is not approved stays blocked; approved drafts can publish; any release can be reverted cleanly.
- **Acceptance Verification**:
  ```bash
  python lab12_governance/demo_lab12.py
  ```
  - Result: the approved release publishes with `status='published'` and `approved=True`; the unapproved release stays `status='draft'` and `approved=False` with the publish block flag set.
  - Rollback check: the published version restores successfully with `restored=True` and a `rolled_back` status, while the blocked draft is not a valid rollback target.
  - Evidence from the command output:
    - `Approved release published: True | status=published`
    - `Blocked publish: False | status=draft`
  - Status: **PASS**.

---

## Lab 13: Discipline-Specific Agents - Domain Specialisation (`lab13_specialists/`)

- **Goal**: plug in domain-specific specialists so the system produces content that matches the relevant operational context instead of generic admin boilerplate.
- **Implementation focus**: `PlacementCoordinatorSpecialist` and `SchedulingCoordinatorSpecialist` validate their inputs and generate checkable outputs with company/batch or proposed-slot extraction.
- **Acceptance bar**: the movement from generic replies to role-specific replies must preserve the approval contract; specialist drafts remain drafts unless the mailbox owner approves them.
- **Acceptance Verification**:
  ```bash
  python lab13_specialists/demo_lab13.py
  ```
  - Result: the placement specialist extracts `LTM` for the 2027 batch and the scheduling specialist identifies `Wednesday at 3:00 PM` while both outputs pass schema validation.
  - Approval contract: `requires_faculty_approval` is not a bypass; it only indicates whether a meeting-specific confirmation is required before a final send.
  - Status: **PASS**.

---

## Lab 14: Capstone - Team-Owned System (`lab14_capstone/`)

- **Goal**: deploy the full worklet as a single, integrated system that uses the earlier contracts rather than rewriting them.
- **Implementation focus**: `CapstoneWorklet` wires the connector, runtime, graph, governance, and specialists into one approved review bundle and exposes a Streamlit shell for the faculty mailbox owner.
- **Acceptance bar**: the mailbox owner can run one session, review the generated triaged inbox and drafts, and publish only approved outputs under the same approval guardrail as the dashboard.
- **Acceptance Verification**:
  ```bash
  python lab14_capstone/demo_lab14.py
  streamlit run lab14_capstone/app.py --server.headless true --server.address 127.0.0.1 --server.port 8502
  ```
  - Result: the demo produces an approved artifact with two specialist drafts published under the governance contract, and the live app loads at `http://127.0.0.1:8502` with the Mailbox Owner Capstone form and controls visible.
  - Status: **PASS**.

---

- **Final stop gate**: Lab 14 is verified green. This completes the Chapter 3 capstone integration and leaves the system in a reviewed, published state with an approved audit trail.
