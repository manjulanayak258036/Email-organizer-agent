=== CHAPTER 3: Email Organizer Agent ===
Agentic AI Worklets — 14-Lab Build Book

Triage, draft, and track faculty email — with faculty approving every reply that goes out.
Human authority: the mailbox owner. Primary output: triaged inbox with draft replies.

--- The 14-Lab Method (Recap) ---
Every worklet in this book is built the same way: as a coordinator-plus-workers agentic system that is grown, one capability at a time, through 14 hands-on labs. This chapter is self-contained — it restates the method, the node-graph legend and the pseudocode conventions before applying them to this worklet — so it can be handed to a team on its own.

The guiding design principle is constant across all worklets: agents draft and flag; a named human approves. No worklet takes a consequential action autonomously — the human authority named in this chapter signs off before anything is published or sent.

The four phases:
- Phase A — Foundations (Labs 1–6): Turn a single agent loop into a tool-using, skill-driven, memory-backed agent that reaches all data through one connector and runs inside a governed runtime with an audit log.
- Phase B — Orchestration (Labs 7–8): Wire the specialist agents into an explicit node graph, then parallelise the per-unit work and merge the best results.
- Phase C — Applied reliability (Labs 9–11): Ground every output in evidence, make the pipeline self-healing on validation failure, and treat the spec as a tested build.
- Phase D — Governance & capstone (Labs 12–14): Add safety, approval, evaluation and rollback; plug in domain specialists; integrate everything into a deployed, team-owned system.

--- Reading the node graph (COLOR LEGEND — this defines the visual/semantic 
    color coding used throughout the worklet's architecture diagrams) ---
- Navy — the apniLeap AURA Coordinator: owns the run-state, plan, budgets and audit log.
- Light blue — specialist agents, each with one responsibility and a typed message contract.
- Amber — the human review gate: a hard stop; the named human is the final authority.
- Green — governed publish/act: versioned, auditable, reversible.
- Dashed grey — coordinator oversight of every agent; a red back-edge is validation → regenerate.

--- Pseudocode conventions ---
- Pseudocode is language-neutral: Coordinator orchestrates; Agent.step(ctx) is one specialist doing its job on the shared run-context; a human gate returns approve / edit / override.
- The blueprint/plan is locked before work begins; validation is a hard gate; the human approves before publish.

=== 3.1 Worklet Overview ===
Faculty inboxes mix urgent administrative requests, student queries, meeting requests, and low-priority notices. Sorting, prioritizing, and replying consistently is time-consuming and easy to fall behind on.

This worklet proposes an Email Organizer Agent that classifies incoming mail, drafts replies for review, extracts action items and meeting requests, and tracks follow-ups — without ever sending anything without faculty approval.

Stakeholders: Faculty

Problems heard:
- Important requests (admin deadlines, student issues) can be buried under routine notices.
- Similar questions get answered from scratch each time instead of reusing a standard response.
- Meeting requests embedded in email threads are easy to miss or double-book against.
- Action items mentioned in passing within longer emails are not tracked anywhere.
- There is no consistent follow-up reminder for emails that were meant to be answered later.

=== 3.2 Target Final Solution (Definition of Done) ===
The capstone (Lab 14) is complete when, for a real case, the worklet turns a request into a validated, evidence-grounded triaged inbox with draft replies that passes every check, is reviewed and approved by the mailbox owner, and is published with a full audit trail — with light human edits, not a rewrite.

Capabilities:
- The Ingestion & Classification Agent tags each incoming email by sender category and content type.
- The Priority & Urgency Agent ranks emails by deadline signals and escalation language.
- The Draft Reply Agent proposes a reply, using the standard-response library where a close match exists.
- The Action-Item Extraction Agent pulls out tasks, deadlines, and commitments into a tracked list.
- The Follow-up/Reminder Agent flags emails marked "reply later" and resurfaces them on schedule.
- The Calendar & Task Sync Agent matches meeting requests to faculty's calendar and proposes slots.

Success metrics (KPIs):
- 100% of validation checks pass before the mailbox owner review (e.g. no email is sent without the owner's approval).
- Every triaged inbox with draft replies is grounded in the actual thread history and the owner's past replies, with an evidence record.
- Zero consequential actions without the mailbox owner's approval; a complete audit trail and one-click rollback.

=== 3.3 System at a Glance — the Node Graph ===
A coordinator-plus-workers system: the apniLeap AURA Coordinator holds the plan, run-state and audit log and drives the pipeline; validation is a hard gate; the human review is a hard stop before publish.

Figure 3 — the Email Organizer Agent agent graph (color-coded per the legend above):
[Navy] apniLeap AURA Coordinator
  ↓ (dashed grey oversight lines fan out to every node below)
[Light blue] Ingestion & Classification
  ↓
[Light blue] Priority & Urgency
  ↓
[Light blue] Draft Reply
  ↓
[Light blue] Action-Item Extraction
  ↓
[Light blue] Follow-up / Reminder
  ↓
[Light blue] Calendar & Task Sync
  ↓
[Amber] Faculty (approve) — hard stop, human gate
  ↓
[Green] Archive & Logging — governed publish/act

End-to-end flow:
- The Ingestion & Classification Agent tags each incoming email by sender category and content type.
- The Priority & Urgency Agent ranks emails by deadline signals and escalation language.
- The Draft Reply Agent proposes a reply, using the standard-response library where a close match exists.
- The Action-Item Extraction Agent pulls out tasks, deadlines, and commitments into a tracked list.
- The Follow-up/Reminder Agent flags emails marked "reply later" and resurfaces them on schedule.
- The Calendar & Task Sync Agent matches meeting requests to faculty's calendar and proposes slots.
- Faculty reviews the draft queue, approves, edits, or discards each draft.
- The Archive & Logging Agent sends approved replies, logs the exchange, and archives resolved items.

=== 3.4 Agent Roster — Roles, Communication & Guardrails ===
# | Agent | Role & communication | Guardrails
0 | apniLeap AURA Coordinator | Watches connected folders, creates the run plan, initializes agents, monitors state. | Never auto-send; enforce inbox access scope and audit logging.
1 | Ingestion & Classification Agent | Tags each email by sender category and content type. | Never expose email content beyond the faculty's own access scope.
2 | Priority & Urgency Agent | Ranks emails by deadline signals and escalation language. | Flag uncertain urgency for faculty judgment rather than guessing.
3 | Draft Reply Agent | Proposes a reply using the standard-response library where applicable. | Draft only; never send without explicit faculty approval.
4 | Action-Item Extraction Agent | Extracts tasks, deadlines, and commitments into a tracked list. | Do not mark an item complete without faculty or task-owner confirmation.
5 | Follow-up / Reminder Agent | Resurfaces "reply later" emails on a faculty-set schedule. | Never let a flagged item silently expire without a reminder.
6 | Calendar & Task Sync Agent | Matches meeting requests to the calendar and proposes slots. | Never confirm a meeting time without faculty approval.
7 | Faculty Review | Reviews the draft queue, approves, edits, or discards. | Faculty decision is final authority for every outgoing reply.
8 | Archive & Logging Agent | Sends approved replies, logs the exchange, archives resolved items. | Keep a full audit log of every reply sent and by whom it was approved.

=== 3.5 Agent Interconnections (Message Map) ===
From | To | Message / payload | When
Coordinator | Ingestion & Classification Agent | run-context + task | run start
Ingestion & Classification Agent | Priority & Urgency Agent | state / partial result | in pipeline
Priority & Urgency Agent | Draft Reply Agent | state / partial result | in pipeline
Draft Reply Agent | Action-Item Extraction Agent | state / partial result | in pipeline
Action-Item Extraction Agent | Follow-up / Reminder Agent | state / partial result | in pipeline
Follow-up / Reminder Agent | Calendar & Task Sync Agent | state / partial result | in pipeline
Calendar & Task Sync Agent | Faculty Review | state / partial result | in pipeline
Faculty Review | Archive & Logging Agent | state / partial result | in pipeline
Archive & Logging Agent | The Mailbox Owner (gate) | draft triaged inbox with draft replies + evidence | for review
The Mailbox Owner (gate) | Coordinator | approve | edit | override | human decision
Coordinator | Governance / Publish | final triaged inbox with draft replies (versioned) | on approval

=== 3.6 Data Model ===
Entity | Key fields
Sender category | Student, admin, collaborator, vendor, or other — used for routing and priority.
Urgency signal | Deadline mentions, escalation language, or explicit priority markers in the email.
Standard response library | Faculty's existing template replies for common questions.
Action-item pattern | Phrases indicating a task, deadline, or commitment embedded in the email body.
Meeting request signal | Proposed dates/times or scheduling language within the email.

=== 3.7 Solution Paradigm — Pseudocode ===

Orchestrator (the whole run):
function run_email_organizer_agent(request):
    ctx = Coordinator.new_run(request)          # isolated, checkpointed
    plan = Coordinator.build_plan(request)       # locked before work begins
    ctx = IngestionClassificationAgent.step(ctx, plan)
    ctx = PriorityUrgencyAgent.step(ctx, plan)
    ctx = DraftReplyAgent.step(ctx, plan)
    ctx = ActionItemExtractionAgent.step(ctx, plan)
    ctx = FollowupReminderAgent.step(ctx, plan)
    ctx = CalendarTaskSyncAgent.step(ctx, plan)
    ctx = FacultyReview.step(ctx, plan)
    ctx = ArchiveLoggingAgent.step(ctx, plan)
    report = ValidationAgent.validate(ctx, plan)  # hard gate
    while not report.passed and attempts < MAX:   # self-healing (Lab 10)
        Coordinator.regenerate(report.failing); report = validate(ctx, plan)
    draft = assemble(ctx)                         # the triaged inbox with draft replies
    decision = TheGate.review(draft)               # HUMAN — final authority
    if decision.approved:
        final = apply(decision.edits, draft)
        Governance.publish(final, version=next()); Audit.log_all()
    return final

Validation (the acceptance gate):
function ValidationAgent.validate(ctx, plan):
    checks = [
        ('no email is sent without the owner's approval', test_0(ctx, plan)),
        ('each draft reply cites its thread context', test_1(ctx, plan)),
        ('priority matches the owner's rules', test_2(ctx, plan)),
        ('no mailbox data leaves the account', test_3(ctx, plan)),
    ]
    failing = [n for n,ok in checks if not ok]
    return Report(passed = not failing, failing = failing, diagnosis = explain(failing))

Connector (one governed surface for all sources):
connector.expose:
    read('the inbox & threads')
    read('contacts & prior replies')
    read('the calendar & task list')
agents.use(connector)   # no agent touches a source directly

--- Worked example — one email thread, end to end ---
Stage | What happens
Plan / slot | The coordinator locks the plan and picks one email thread to work — its constraints fixed before any content is chosen.
Source candidate | A retrieval agent proposes a candidate for this email thread from the inbox & threads, with provenance.
Grounded candidate | A generation agent produces a fresh candidate grounded in the actual thread history and the owner's past replies, attaching an evidence record (source, scope, tags).
Screen & select | Candidates are calibrated and screened; the best-aligned one that satisfies the plan is selected, the rest logged.
Validation | The result is checked (no email is sent without the owner's approval; priority matches the owner's rules); on failure only this email thread is regenerated.
Human review | The Mailbox Owner sees the draft triaged inbox with draft replies with its evidence and validation report, and approves, edits or overrides.
Publish & audit | On approval the governed publish versions the triaged inbox with draft replies, records the audit trail, and updates history for future runs.

=== 3.8 Hybrid Execution Methodology ===
Stage | Execution mode & coordinator behavior
Gate 1: ingestion | Sequential — classification must complete before priority ranking or drafting begins.
Parallel triage | Parallel — Priority Agent, Action-Item Agent, and Calendar Sync Agent all work off the classified inbox simultaneously.
Draft generation | Parallel — Draft Reply Agent works across all queued emails independently.
Faculty approval | Sequential — nothing is sent until faculty reviews the draft queue.
Send and archive | Sequential after approval — Archive & Logging Agent sends and logs each approved reply in turn.
Follow-up scheduling | Parallel, ongoing — runs independently of the daily triage cycle.

=== 3.9 Dashboard Template ===
What the mailbox owner sees to review, approve and monitor.
Panel | Shows
Triaged inbox | Emails ranked by sender category and urgency.
Draft-reply queue | Proposed replies awaiting faculty approval.
Action-item list | Tasks, deadlines, and commitments extracted from mail.
Follow-up digest | "Reply later" items resurfacing on schedule, plus response-time metrics.

=== 3.10 The 14-Lab Evolution ===
[Overview diagram: 4 phases as described above, Labs 1-14]

--- Lab 1 — Agent vs Chatbot — the triaged inbox with draft replies planner loop ---
Phase: A · Foundations   Goal: Establish the agent loop (clarify → plan → revise) instead of a one-shot chatbot answer.
What it adds: A minimal planner that clarifies the request, proposes a plan for producing the triaged inbox with draft replies, and revises on feedback — the seed this worklet grows from.
Inputs: Free-text request; core parameters.
Outputs: A clarified request + an editable outline plan for the triaged inbox with draft replies.
Agents/nodes: Coordinator (loop only).
Deliverable & acceptance: A notebook agent that clarifies, plans and revises a triaged inbox with draft replies outline. Accept: Given a vague request it asks at least two clarifying questions and yields a coherent, editable plan.
Nodes activated: Coordinator loop (no specialist nodes yet).
Pitfall to avoid: Don't answer in one shot — without clarify/revise it's a chatbot, not an agent.
Pseudocode:
req = clarify(user_request)              # ask until inputs complete
plan = propose_plan(req)                 # outline for the triaged inbox with draft replies
while user.wants_changes(plan): plan = revise(plan, user.feedback)
return plan                              # not final — a structured plan

--- Lab 2 — Tool-Using Agent — call data & compute ---
Phase: A · Foundations   Goal: Give the agent tools it must call to act, rather than answering from memory.
What it adds: Readers for the inbox & threads and contacts & prior replies, plus a domain calculator/checker, so the planner acts on real data.
Inputs: the inbox & threads; contacts & prior replies; parameters.
Outputs: Verified computed values and parsed inputs.
Agents/nodes: Coordinator + tool layer.
Deliverable & acceptance: An agent that reads the inbox & threads and computes/validates through typed tools. Accept: Key numbers and lookups always go through tools, never hand-done in the prompt.
Nodes activated: Tool layer feeding the early data agents.
Pitfall to avoid: Never assert a fact in the prompt that a tool should verify.
Pseudocode:
a = tool.read('the inbox & threads')
b = tool.read('contacts & prior replies')
v = tool.compute(a, b)
assert v.valid

--- Lab 3 — Skill Creation — reusable plan & format skills ---
Phase: A · Foundations   Goal: Package repeatable capability as reusable, schema-typed skills.
What it adds: A plan/blueprint skill and a formatting skill that renders the triaged inbox with draft replies — both reusable across cases.
Inputs: Parsed inputs; template spec.
Outputs: A locked plan object; a formatted triaged inbox with draft replies shell.
Agents/nodes: Planning and assembly emerge as skills.
Deliverable & acceptance: Two callable skills with schemas, invoked by the agent. Accept: The same skill works for two different cases without code changes.
Nodes activated: Plan node + Assembly node (as skills).
Pitfall to avoid: Keep skills case-agnostic and typed; hard-coding one case breaks reuse.
Pseudocode:
skill plan(inputs) -> Plan: return expand(inputs).lock()
skill format_triaged(result, template) -> Document

--- Lab 4 — Memory & Retrieval — state vs stored ---
Phase: A · Foundations   Goal: Separate short-term run state from long-term stored knowledge.
What it adds: Session state (the current draft) vs stored reference — the inbox & threads and the history of past email threads — retrieved by tags and by similarity.
Inputs: the inbox & threads; history of prior email threads; current draft.
Outputs: Tag- and similarity-based retrieval.
Agents/nodes: Retrieval agent; foundations of later screening.
Deliverable & acceptance: Retrieval over the store + history with tag filters and embedding similarity. Accept: For a given task, retrieval returns correctly-tagged candidates and similar prior items.
Nodes activated: Retrieval node; seeds validation/no-repeat.
Pitfall to avoid: Don't conflate run state with the archive — mixing them corrupts the baseline.
Pseudocode:
state.draft = candidate                       # short-term
hits = retrieve(store, tags)                  # long-term
prior = retrieve(history, embed(candidate), k=5)  # similarity

--- Lab 5 — MCP-Style Connector — one server for all sources ---
Phase: A · Foundations   Goal: Expose every data source through one typed connector.
What it adds: A single connector fronting the inbox & threads, contacts & prior replies and the calendar & task list so every agent reaches data the same governed way.
Inputs: The worklet's data sources.
Outputs: A uniform, typed tool surface.
Agents/nodes: Connector used by all data-facing agents.
Deliverable & acceptance: A connector server with typed endpoints and auth; agents call only through it. Accept: All data access goes through the connector; swapping a source needs no agent change.
Nodes activated: Connector under the data agents.
Pitfall to avoid: No agent should touch a source directly; a bypass defeats governance later.
Pseudocode:
connector.expose:
    read('the inbox & threads')
    read('contacts & prior replies')
    read('the calendar & task list')
agents.use(connector)   # no agent touches a source directly

--- Lab 6 — Runtime — skills, tools, memory, audit ---
Phase: A · Foundations   Goal: Run the agent inside a controlled runtime with a full audit log.
What it adds: A runtime binding skills + tools + memory behind the loop, enforcing budgets and approval gates and logging every step — the backbone later labs plug into.
Inputs: Skills (Lab 3), connector (Lab 5), memory (Lab 4).
Outputs: A governed run with audit + checkpoints.
Agents/nodes: Coordinator hardened into the runtime controller.
Deliverable & acceptance: Runtime wrapping the agent: budgets, gates, checkpoint/resume, audit log. Accept: Every action is logged with inputs/outputs; a crashed run resumes from its last checkpoint.
Nodes activated: Coordinator runtime around all nodes.
Pitfall to avoid: Log inputs and outputs, not just messages; checkpoint before risky steps or resume loses state.
Pseudocode:
run = Runtime(budget=B, gates=[publish])
for step in agent.loop():
    audit.log(step.intent, step.action, step.result)
    if step.risky: wait_for_approval(step)
    checkpoint(run.state)

--- Lab 7 — Agentic Node Graph — the full pipeline ---
Phase: B · Orchestration   Goal: Wire the specialist agents into one explicit graph with state and branching.
What it adds: The complete pipeline as a node graph: Ingestion & Classification Agent, Priority & Urgency Agent, Draft Reply Agent → … → the mailbox owner gate → publish, with a validation → regenerate back-edge.
Inputs: All Phase-A skills/agents.
Outputs: An executable graph producing a first end-to-end draft.
Agents/nodes: All core agents connected (see this chapter's node graph).
Deliverable & acceptance: A graph runner that produces a full triaged inbox with draft replies draft end to end. Accept: One command yields a validated triaged inbox with draft replies draft end to end.
Nodes activated: All core nodes + the back-edge.
Pitfall to avoid: Bound the retry edge — an unbounded regenerate loop can spin forever.
Pseudocode:
graph.chain(ingest -> plan -> workers -> validate)
graph.edge(validate --fail--> workers)     # bounded retry
graph.edge(validate --pass--> assemble -> gate -> publish)

--- Lab 8 — Parallel Swarm — many email threads, then merge ---
Phase: B · Orchestration   Goal: Parallelise the per-unit work and select the best.
What it adds: Several worker agents process email threads in parallel; a merge/selector picks the best per the plan — cutting latency and improving quality.
Inputs: Locked plan; per-unit work items.
Outputs: Best-of-N results merged into one compliant output.
Agents/nodes: Parallel workers + a Merge selector under the Coordinator.
Deliverable & acceptance: A fan-out/fan-in that processes all units and merges by alignment to the plan. Accept: Parallel run matches or beats sequential quality at lower wall-clock time.
Nodes activated: Parallel worker fan-out + merge.
Pitfall to avoid: Merge strictly by plan alignment; picking the 'nicest' output quietly breaks coverage.
Pseudocode:
results = parallel_map(process_email, plan.units)
output = merge(results, key=alignment_to(plan))

--- Lab 9 — Deep Research — ground & evidence ---
Phase: C · Applied reliability   Goal: Ground every output in cited, in-scope evidence.
What it adds: For each email thread the agent builds an evidence record grounded in the actual thread history and the owner's past replies, so validity is auditable and out-of-scope content can't slip through.
Inputs: the actual thread history and the owner's past replies; candidate outputs.
Outputs: An evidence record per unit; a paper-level evidence table.
Agents/nodes: Generation + grounding step feeding Validation.
Deliverable & acceptance: Each candidate carries an evidence record; an evidence table is produced. Accept: Every output maps to an in-scope source; ungrounded candidates are rejected.
Nodes activated: Grounding step into the validation check.
Pitfall to avoid: Require a real source; a plausible-sounding but ungrounded item must be rejected, not kept.
Pseudocode:
for c in candidates:
    ev = research(c, source="the actual thread history and the owner's past replies")
    if not ev.in_scope: reject(c)
    c.evidence = ev

--- Lab 10 — Ops Resilience — validate, diagnose, fix ---
Phase: C · Applied reliability   Goal: Make the pipeline self-healing when validation fails.
What it adds: When a check fails (no email is sent without the owner's approval; each draft reply cites its thread context), the agent diagnoses the exact failing constraint and regenerates only the offending part.
Inputs: Validation report; current output.
Outputs: A repaired, passing output with a diagnosis log.
Agents/nodes: Validation agent + Coordinator's regenerate loop.
Deliverable & acceptance: Failure-injection tests showing automatic diagnosis and targeted repair. Accept: Injected faults are detected and fixed within the retry budget.
Nodes activated: Validation node + self-healing loop.
Pitfall to avoid: Regenerate only the failing part — rebuilding everything wastes budget and churns good work.
Pseudocode:
report = validate(output, plan)
while not report.passed and attempts < BUDGET:
    regenerate(report.failing); report = validate(output, plan)
if not report.passed: escalate(report)    # to the human

--- Lab 11 — SDLC Factory — spec → tested output ---
Phase: C · Applied reliability   Goal: Treat the plan as a spec and the output as a tested implementation.
What it adds: The worklet becomes a factory: plan in, a triaged inbox with draft replies out that provably passes an automated acceptance suite before the mailbox owner sees it.
Inputs: The locked plan (spec); the acceptance suite.
Outputs: A result plus a green test report.
Agents/nodes: Validation as the test harness; Coordinator as the build.
Deliverable & acceptance: A 'build' command: plan → triaged inbox with draft replies + passing acceptance report. Accept: No triaged inbox with draft replies advances to the mailbox owner without a fully passing acceptance report.
Nodes activated: Validation gates the whole graph.
Pitfall to avoid: The acceptance suite is the gate; never let a result skip to the human without a green report.
Pseudocode:
artifact = build(plan)                    # graph run (Lab 7/8/10)
report = acceptance_suite(artifact, plan)
require report.all_pass                   # gate before human review

--- Lab 12 — Safety & Governance — approval, eval, rollback ---
Phase: D · Governance & capstone   Goal: Add confidentiality, approval, evaluation and rollback.
What it adds: Access control and confidentiality, the mailbox owner approval gate as a hard stop, evaluation metrics, versioning and one-click rollback.
Inputs: Draft-vs-approved states; role permissions; metrics.
Outputs: A governed, reversible release.
Agents/nodes: Governance & Audit agent; the human gate formalised.
Deliverable & acceptance: Approval workflow + metrics + rollback, with confidentiality controls. Accept: Only the mailbox owner-approved results publish; any release rolls back cleanly.
Nodes activated: Human gate + governance node.
Pitfall to avoid: Confidentiality and rollback are requirements, not extras.
Pseudocode:
require actor.can_approve and out.status=='draft'
final = apply(human.edits, out); final.status='approved'
governance.publish(final, version=v+1); metrics.record(...)
on rollback(v): restore(version=v)

--- Lab 13 — Discipline-Specific Agents — domain specialisation ---
Phase: D · Governance & capstone   Goal: Specialise the worklet to its domain variants.
What it adds: Pluggable specialists — category handlers (scheduling, approvals, newsletters, VIP senders) — so outputs match the specific style and constraints of each case.
Inputs: Domain profile; the work item.
Outputs: Domain-appropriate outputs with correct schemes.
Agents/nodes: Specialist plugged into the generation node.
Deliverable & acceptance: A specialist producing domain-correct triaged inbox with draft replies. Accept: Specialist outputs use valid domain patterns and produce checkable results.
Nodes activated: Specialist into the generation node.
Pitfall to avoid: Every specialist output needs a checkable scheme; clever but vague outputs are unusable.
Pseudocode:
specialist = registry.get(domain)
out = specialist.generate(item)
GenerationAgent.use(specialist)

--- Lab 14 — Capstone — team-owned system ---
Phase: D · Governance & capstone   Goal: Integrate everything into a deployed, team-owned system.
What it adds: The full worklet: connector + runtime + node graph + parallel work + grounding + self-healing + governance + specialists, with a mailbox owner dashboard — delivered and demoed end to end.
Inputs: All prior lab deliverables.
Outputs: A deployed worklet: request → approved, published triaged inbox with draft replies.
Agents/nodes: All agents under the Coordinator (this chapter's node graph).
Deliverable & acceptance: Deployed system + the mailbox owner dashboard + audit trail + a demo on a real case. Accept: The Mailbox Owner produces an approved, validated triaged inbox with draft replies in one session.
Nodes activated: Every node, deployed.
Pitfall to avoid: Integrate, don't rewrite — if the labs kept the contracts, the capstone is wiring.
Pseudocode:
system = deploy(connector, runtime, graph, governance)
artifact = system.run(request)            # the triaged inbox with draft replies
dashboard.show(artifact, metrics, audit)

=== 3.11 Reference Architecture, Pilot & MVP ===

Reference architecture:
- Data capture: connected inbox folders and a faculty-maintained standard-response library.
- Data layer: canonical schema for sender category, urgency, action items, and meeting requests.
- AI layer: classification, priority ranking, draft generation, and extraction agents.
- Workflow layer: review queue, calendar sync, follow-up scheduling, dashboard.
- Governance layer: access scope, audit logging of sends, no-auto-send enforcement.

Pilot artifacts:
- A one-week triaged inbox view with priority ranking.
- A draft-reply queue using an initial standard-response library of 10–15 common questions.
- An action-item and meeting-request extraction list for the same week.
- A follow-up digest for emails flagged "reply later."

Suggested MVP roadmap:
Order | Capability | What it delivers | Agents involved
1 | Ingestion & classification | Tag and categorize incoming mail. | Coordinator, Ingestion & Classification Agent.
2 | Priority ranking + draft replies | Rank urgency; draft replies from a starter template library. | Priority Agent, Draft Reply Agent.
3 | Action-item extraction | Pull tasks/deadlines into a tracked list. | Action-Item Extraction Agent.
4 | Follow-up reminders | Resurface "reply later" items on schedule. | Follow-up / Reminder Agent.
5 | Calendar sync | Match meeting requests to calendar availability. | Calendar & Task Sync Agent.
6 | Full audit dashboard | Reply log, approval history, response-time metrics. | Archive & Logging Agent.

Risks & mitigations:
Risk | Why it matters | Mitigation (where handled)
Plan drift | individual results deviate from the locked plan | Lock the plan (Lab 3/7); validation rejects any deviation before the human sees it.
Ungrounded output | content not backed by the actual thread history and the owner's past replies | Grounded generation with an evidence record per unit (Lab 9); ungrounded items are rejected.
Failed checks slip through | a result violates a rule (no email is sent without the owner's approval) | Validation is a hard gate (Lab 10/11); failing results are diagnosed and regenerated, never advanced.
Runaway loops | the regenerate loop never converges | Bound MAX_ATTEMPTS (Lab 7/10); on exhaustion, escalate to the mailbox owner with a diagnosis.
Over-automation | the system acts without the mailbox owner | The human gate is a hard stop; all outputs are drafts; edits and overrides are effortless and logged (Lab 12).

=== 3.12 Guardrails, Metrics, Milestones & Glossary ===

Guardrails:
- Never send an email without explicit faculty approval.
- Never mark a task or action item complete without confirmation.
- Never confirm a meeting time without faculty approval.
- Keep an audit log of every reply sent and every approval given.
- Restrict inbox access strictly to the faculty's own account and role.

Delivery milestones:
Week | Labs | Focus | Exit deliverable
Week 1 | Labs 1–3 | Planner loop, tools, reusable skills | Runnable planner + core skill
Week 2 | Labs 4–6 | Memory/retrieval, connector, governed runtime | Data via connector; audited runs
Week 3 | Labs 7–8 | Full node graph + parallel processing | End-to-end draft — shared with faculty
Week 4 | Labs 9–10 | Grounding + self-healing validation | Grounded output; auto-repair on faults
Week 5 | Labs 11–12 | Tested build + safety/governance | Tested artifact; approval, metrics, rollback
Week 6 | Labs 13–14 | Domain specialisation + capstone | Deployed system + demo on a real case

Checkpoint: from the 3rd week, worklets are shared with all faculty for feedback — plan the Week-3 end-to-end draft (Labs 7–8) to be demo-ready.

Glossary:
Term | Meaning
Coordinator | The orchestrator agent that owns run-state, plan, budgets and the audit log.
Node graph | The explicit wiring of agents, gates and back-edges for one worklet.
Human gate | The approval step; the named human is the final authority.
Grounding | Linking an output to a real in-scope source (evidence).
Validation | The automated acceptance gate a result must pass before human review.
Blueprint / plan | The locked specification the pipeline obeys.