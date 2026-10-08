# Review-Ready Dashboard

## Purpose

This Streamlit dashboard is introduced before the capstone so the mailbox owner
can review the Chapter 3 section 3.9 dashboard panels from a clean UI instead
of terminal output.

It uses real pipeline components:

- Lab 5 `MCPStyleConnector` for live/fixture data access and provenance.
- Lab 6 `GovernedRuntime` through the Lab 7 graph runner for audited execution.
- `core.auth.send_email_guarded()` for approved draft sending.
- `core.audit.AuditLogger.read_all()` for the live audit trail.

## Run

```bash
streamlit run dashboard/app.py
```

## Panels

The UI implements the four Chapter 3 section 3.9 panels:

| Panel | Contents |
|------|----------|
| Triaged Inbox | Emails ranked by sender category and urgency |
| Draft-Reply Queue | Proposed replies awaiting faculty approval |
| Action-Item List | Tasks, deadlines, and commitments extracted from mail |
| Follow-up Digest | Reply-later resurfacing plus response-time metrics |

An additional Audit Trail tab shows the real JSONL audit log so the governed
runtime claim is visible during review.

## Review-Ready SaaS Polish & Design System

The dashboard incorporates a custom SaaS theme and layout enhancements:
- **Custom Theme Configuration (`.streamlit/config.toml`)**: Slate/navy dark foundation (`#0F172A`, `#1E293B`), neutral background (`#F8FAFC`), and subtle enterprise blue accent (`#2563EB`).
- **Audit Table Safe Serialization**: Resolves PyArrow mixed-type crashes by recursively JSON-serializing nested dictionaries/lists in `safe_audit_dataframe()`.
- **Dynamic Thread Ingestion**: Configurable slider (5 to 50 threads) with automated Gmail API pagination in `MCPStyleConnector._gmail_read_threads()`.
- **Card-Based Draft Review**: Split layout with editable draft body, intent-colored action buttons (Approve & Send, Save Changes, Discard), and metadata/citation badge cards.
- **Modern Deprecation-Free API**: Cleaned up all `use_container_width` references to `width='stretch'` across dataframes.

## State Model

Each draft tracks explicit review state (`draft`, `sent`, `discarded`) in
Streamlit session state. This keeps the approval data model aligned with the
later Lab 12 approval workflow/rollback work and the final Lab 14 mailbox-owner
dashboard without requiring a rewrite.

