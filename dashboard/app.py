"""Review-ready Streamlit dashboard for the Email Organizer Agent.

Run with:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import datetime
import html
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.audit import AuditLogger
from core.auth import GoogleAuthManager, send_email_guarded
from core.models import ApprovalStatus, DraftReply, TriagedInbox
from lab07_node_graph.graph import AgenticNodeGraph, GraphRunResult


AUDIT_PATH = ROOT / "audit_log.jsonl"
CHECKPOINT_PATH = ROOT / "runtime_checkpoint.jsonl"


# =============================================================================
# Custom SaaS Design System & CSS Injection
# =============================================================================

CUSTOM_CSS = """
<style>
/* ---------------- Global & Typography ---------------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #0F172A;
    background: #F4F9FF;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {background: rgba(11, 31, 58, 0.96); backdrop-filter: blur(8px);}

/* ---------------- Legend & Theme Palette ---------------- */
.theme-navy { background: #0B1F3A; color: #E2E8F0; }
.theme-agent { background: #EAF5FF; border: 1px solid #BFDBFE; }
.theme-amber { background: #FFF5D6; border: 1px solid #FCD34D; }
.theme-green { background: #E8F8EE; border: 1px solid #A7F3D0; }

/* ---------------- Hero / Header ---------------- */
.saas-hero {
    background: linear-gradient(135deg, #0B1F3A 0%, #132F52 100%);
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 0.9rem;
    color: #F8FAFC;
    box-shadow: 0 4px 12px rgba(11, 31, 58, 0.08);
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: 68px;
}

.saas-hero-title {
    font-size: 1.2rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
    color: #FFFFFF;
}

.saas-hero-subtitle {
    font-size: 0.76rem;
    color: #B9C8DA;
    margin-top: 0.15rem;
    margin-bottom: 0;
    line-height: 1.4;
}

.saas-hero-badge {
    background: rgba(96, 165, 250, 0.18);
    border: 1px solid rgba(147, 197, 253, 0.45);
    color: #DCEEFF;
    padding: 0.4rem 0.7rem;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

/* ---------------- Compact Summary Row ---------------- */
.summary-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    margin: 0 0 0.75rem 0;
    padding: 0.55rem 0.8rem;
    background: #F8FBFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    color: #334155;
    font-size: 0.78rem;
    font-weight: 600;
}

.summary-pill {
    display: inline-flex;
    align-items: center;
    padding: 0.32rem 0.62rem;
    border-radius: 999px;
    background: #EAF5FF;
    border: 1px solid #DBEAFE;
    color: #0F172A;
}

.summary-pill strong {
    margin-right: 0.2rem;
}

/* ---------------- High-end review panels ---------------- */
.insight-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    margin: 0.85rem 0 1.1rem 0;
}

.insight-card {
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 0.8rem 0.9rem;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03);
}

.insight-label {
    display: block;
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748B;
    margin-bottom: 0.35rem;
    font-weight: 700;
}

.insight-card strong {
    display: block;
    font-size: 1rem;
    color: #0F172A;
    margin-bottom: 0.18rem;
}

.insight-card span {
    color: #475569;
    font-size: 0.75rem;
    line-height: 1.5;
}

.review-guide {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 0.9rem 1rem 0.75rem 1rem;
    margin: 0.2rem 0 1rem 0;
}

.review-guide h4 {
    margin: 0 0 0.55rem 0;
    color: #0F172A;
    font-size: 0.9rem;
}

.review-guide ul {
    margin: 0;
    padding-left: 1.1rem;
    color: #475569;
    font-size: 0.78rem;
    line-height: 1.7;
}

.labs-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.7rem;
    margin: 1rem 0 1.4rem 0;
}

.lab-card {
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 0.7rem 0.65rem;
    min-height: 112px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.lab-card.pass {
    border-left: 4px solid #22C55E;
}

.lab-card.active {
    border-left: 4px solid #60A5FA;
}

.lab-card.pending {
    border-left: 4px solid #F59E0B;
}

.lab-card .lab-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.35rem;
}

.lab-card .lab-no {
    font-size: 0.72rem;
    font-weight: 700;
    color: #0F172A;
}

.lab-card .lab-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.18rem 0.46rem;
    border-radius: 999px;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.lab-card.pass .lab-badge {
    background: #DCFCE7;
    color: #166534;
}

.lab-card.active .lab-badge {
    background: #DBEAFE;
    color: #1D4ED8;
}

.lab-card.pending .lab-badge {
    background: #FEF3C7;
    color: #92400E;
}

.lab-card .lab-title {
    font-size: 0.8rem;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.35;
    margin-bottom: 0.28rem;
}

.lab-card .lab-desc {
    font-size: 0.68rem;
    line-height: 1.5;
    color: #475569;
}

/* ---------------- Gmail-style list rows ---------------- */
.gmail-list {
    border-top: 1px solid #E2E8F0;
    border-bottom: 1px solid #E2E8F0;
    background: #FFFFFF;
}

.gmail-row {
    display: grid;
    grid-template-columns: minmax(120px, 180px) minmax(240px, 1fr) auto 72px;
    align-items: center;
    gap: 0.65rem;
    min-height: 48px;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid #EEF2F7;
    background: #FFFFFF;
    transition: background 0.15s ease;
}

.gmail-item {
    display: block;
    border-bottom: 1px solid #EEF2F7;
    background: #FFFFFF;
}

.gmail-item:last-child {
    border-bottom: none;
}

.gmail-summary {
    display: block;
    list-style: none;
    cursor: pointer;
    margin: 0;
}

.gmail-summary::-webkit-details-marker {
    display: none;
}

.gmail-summary:hover .gmail-row {
    background: #F8FBFF;
}

.gmail-item[open] .gmail-summary {
    background: #F8FBFF;
}

.gmail-sender {
    font-size: 0.8rem;
    color: #1E293B;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.gmail-sender.unread {
    font-weight: 700;
    color: #0F172A;
}

.gmail-subject {
    min-width: 0;
    font-size: 0.8rem;
    color: #0F172A;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 600;
}

.gmail-preview {
    color: #64748B;
    font-weight: 400;
    margin-left: 0.35rem;
}

.gmail-details {
    padding: 0.7rem 0.75rem 0.85rem 0.75rem;
    background: #F8FBFF;
    border-top: 1px solid #EEF2F7;
    color: #334155;
    font-size: 0.8rem;
    line-height: 1.65;
}

.gmail-action-check {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
    color: #0F172A;
    font-weight: 600;
}

.gmail-action-check input {
    width: 16px;
    height: 16px;
    accent-color: #0B1F3A;
}

.gmail-chips {
    display: flex;
    justify-content: flex-end;
    gap: 0.35rem;
    flex-wrap: wrap;
}

.gmail-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.18rem 0.52rem;
    border-radius: 999px;
    font-size: 0.66rem;
    line-height: 1;
    font-weight: 700;
    letter-spacing: 0.02em;
    border: 1px solid transparent;
    white-space: nowrap;
}

.gmail-chip.urgent { background: #FEE2E2; color: #B91C1C; border-color: #FCA5A5; }
.gmail-chip.high { background: #FFEDD5; color: #C2410C; border-color: #FDBA74; }
.gmail-chip.medium { background: #FEF3C7; color: #A16207; border-color: #FCD34D; }
.gmail-chip.low { background: #DBEAFE; color: #1D4ED8; border-color: #93C5FD; }
.gmail-chip.admin { background: #E0F2FE; color: #075985; border-color: #BAE6FD; }
.gmail-chip.student { background: #DCFCE7; color: #166534; border-color: #86EFAC; }
.gmail-chip.collaborator { background: #F3E8FF; color: #7E22CE; border-color: #D8B4FE; }
.gmail-chip.vendor { background: #F1F5F9; color: #475569; border-color: #CBD5E1; }
.gmail-chip.pending { background: #FFF5D6; color: #A16207; border-color: #FCD34D; }
.gmail-chip.approved { background: #DCFCE7; color: #166534; border-color: #86EFAC; }
.gmail-chip.sent { background: #DCFCE7; color: #15803D; border-color: #BBF7D0; }
.gmail-chip.draft { background: #FEF3C7; color: #A16207; border-color: #FCD34D; }
.gmail-chip.neutral { background: #F1F5F9; color: #475569; border-color: #E2E8F0; }
.gmail-chip.tertiary { background: #EAF5FF; color: #1D4ED8; border-color: #BFDBFE; }

.gmail-time {
    font-size: 0.72rem;
    color: #64748B;
    text-align: right;
    white-space: nowrap;
    font-weight: 600;
}

.gmail-details {
    margin-top: 0.2rem;
    background: #F8FBFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 0.75rem 0.9rem;
    color: #334155;
    font-size: 0.8rem;
    line-height: 1.6;
}

/* ---------------- Tabs ---------------- */
div[data-testid="stTabs"] button[role="tab"] {
    font-size: 0.88rem;
    font-weight: 600;
    color: #475569;
    padding: 0.72rem 1rem;
    border-radius: 8px 8px 0 0;
    transition: color 0.15s ease;
    background: #F8FBFF;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #0B1F3A !important;
    border-bottom-color: #0B1F3A !important;
    font-weight: 700;
    background: #EAF5FF;
}

/* ---------------- Card Containers ---------------- */
.saas-card {
    background: #EAF5FF;
    border: 1px solid #BFDBFE;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
}

.saas-card:hover {
    border-color: #93C5FD;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.07);
}

/* ---------------- Status & Urgency Badges ---------------- */
.badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-right: 6px;
}

.badge-urgent { background: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; }
.badge-high   { background: #FFEDD5; color: #C2410C; border: 1px solid #FDBA74; }
.badge-medium { background: #FEF3C7; color: #A16207; border: 1px solid #FCD34D; }
.badge-low    { background: #DBEAFE; color: #1D4ED8; border: 1px solid #93C5FD; }
.badge-admin  { background: #E0F2FE; color: #075985; border: 1px solid #BAE6FD; }
.badge-student { background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }
.badge-collaborator { background: #F3E8FF; color: #7E22CE; border: 1px solid #D8B4FE; }
.badge-vendor { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }
.badge-draft     { background: #FEF3C7; color: #A16207; border: 1px solid #FCD34D; }
.badge-approved  { background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }
.badge-pending  { background: #FFF5D6; color: #A16207; border: 1px solid #FCD34D; }
.badge-sent      { background: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; }
.badge-discarded { background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }

.legend-guide {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    align-items: center;
    padding: 0.4rem 0.75rem;
    margin: 0 0 0.75rem 0;
    background: #F8FBFF;
    border: 1px solid #E2E8F0;
    border-radius: 999px;
    max-width: 780px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.75);
}

.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    color: #475569;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}

.legend-swatch {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    display: inline-block;
    border: 1px solid rgba(15, 23, 42, 0.15);
}

.legend-swatch.navy { background: #0B1F3A; }
.legend-swatch.agent { background: #EAF5FF; }
.legend-swatch.amber { background: #FFF5D6; }
.legend-swatch.green { background: #E8F8EE; }

div[data-testid="stCheckbox"] {
    pointer-events: auto !important;
    position: relative;
    z-index: 1;
    display: inline-flex !important;
    align-items: center !important;
}

div[data-testid="stCheckbox"] label {
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.55rem !important;
    pointer-events: auto !important;
    cursor: pointer;
}

div[data-testid="stCheckbox"] input {
    width: 16px !important;
    height: 16px !important;
    margin: 0 !important;
    accent-color: #0B1F3A !important;
    pointer-events: auto !important;
    cursor: pointer;
}

div[data-testid="stCheckbox"] span {
    pointer-events: auto !important;
    cursor: pointer;
}

/* ---------------- Draft Card Typography & Sections ---------------- */
.draft-card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid #D6E9FF;
    padding-bottom: 0.75rem;
}

.draft-subject {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0F172A;
    margin: 0 0 0.25rem 0;
}

.draft-meta {
    font-size: 0.82rem;
    color: #475569;
}

.draft-meta strong {
    color: #0F172A;
}

.draft-meta-box {
    background: #F8FBFF;
    border: 1px solid #BFDBFE;
    border-radius: 8px;
    padding: 0.85rem;
    font-size: 0.82rem;
    color: #334155;
    margin-bottom: 0.85rem;
}

/* ---------------- Empty State ---------------- */
.saas-empty-state {
    text-align: center;
    padding: 3rem 1.5rem;
    background: #F8FBFF;
    border: 1.5px dashed #BFDBFE;
    border-radius: 12px;
    color: #475569;
    margin: 1.5rem 0;
}

.saas-empty-icon {
    font-size: 2.2rem;
    margin-bottom: 0.5rem;
    display: block;
}

.saas-empty-title {
    font-size: 1rem;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 0.25rem;
}

.saas-empty-desc {
    font-size: 0.85rem;
    color: #475569;
}

/* ---------------- Button Polish ---------------- */
div[data-testid="stButton"] button {
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 0.5rem 1rem;
    transition: all 0.15s ease;
}

div[data-testid="stButton"] button:hover {
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
</style>
"""


# =============================================================================
# Helper Utilities
# =============================================================================

def safe_audit_dataframe(entries: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format audit entries safely for PyArrow by normalizing all complex fields to strings."""
    if not entries:
        return pd.DataFrame()

    safe_rows = []
    for e in entries:
        row = {}
        for k, v in e.items():
            if isinstance(v, (dict, list)):
                try:
                    row[k] = json.dumps(v, default=str)
                except Exception:
                    row[k] = str(v)
            elif v is None:
                row[k] = ""
            else:
                row[k] = str(v) if not isinstance(v, (int, float, bool)) else v
        safe_rows.append(row)

    df = pd.DataFrame(safe_rows)
    # Reorder columns logically if present
    desired_order = [
        "timestamp",
        "agent",
        "action",
        "guardrail_passed",
        "input_summary",
        "result_summary",
        "intent",
        "metadata",
    ]
    present_order = [col for col in desired_order if col in df.columns]
    remaining = [col for col in df.columns if col not in present_order]
    return df[present_order + remaining]


def build_graph_result(max_results: int) -> GraphRunResult:
    graph = AgenticNodeGraph(max_retries=2)
    return graph.run(max_results=max_results)


def ensure_state(result: GraphRunResult) -> None:
    if "draft_states" not in st.session_state:
        st.session_state.draft_states = {}
    if "draft_bodies" not in st.session_state:
        st.session_state.draft_bodies = {}

    inbox = result.triaged_inbox
    if not inbox:
        return
    for item in inbox.items:
        if not item.draft_reply:
            continue
        draft = item.draft_reply
        st.session_state.draft_states.setdefault(
            draft.draft_id,
            {
                "status": draft.status.value,
                "sent_message_id": None,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        )
        st.session_state.draft_bodies.setdefault(draft.draft_id, draft.body)


def audit_logger() -> AuditLogger:
    return AuditLogger(log_path=str(AUDIT_PATH))


def triaged_rows(inbox: TriagedInbox) -> List[Dict[str, Any]]:
    rows = []
    for item in sorted(inbox.items, key=lambda i: i.urgency_score, reverse=True):
        full_body = getattr(item, "body_preview", None) or (item.rationale if item.rationale else item.subject)
        preview = full_body[:80] + ("..." if len(full_body) > 80 else "")
        rows.append(
            {
                "Score": item.urgency_score,
                "Urgency": item.urgency.value.upper(),
                "Category": item.category.value.capitalize(),
                "Sender": item.sender,
                "Subject": item.subject,
                "Preview": preview,
                "Full Body": full_body,
                "Draft Generated": "Yes" if item.draft_reply else "No",
                "Action Items": len(item.action_items),
                "Reply Later": "Yes" if item.reply_later else "No",
            }
        )
    return rows


def action_rows(inbox: TriagedInbox) -> List[Dict[str, Any]]:
    rows = []
    for item in inbox.items:
        for action in item.action_items:
            rows.append(
                {
                    "Thread ID": action.thread_id,
                    "Task Description": action.task,
                    "Deadline": action.deadline or "None specified",
                    "Assigned Owner": action.owner,
                    "Confirmed by Faculty": "Yes" if action.confirmed else "No",
                }
            )
    return rows


def followup_rows(inbox: TriagedInbox) -> List[Dict[str, Any]]:
    rows = []
    for item in inbox.items:
        if item.reply_later:
            rows.append(
                {
                    "Follow-up Type": "Reply Later",
                    "Thread ID": item.thread_id,
                    "Subject": item.subject,
                    "Resurface Timing": item.resurface_date or "Next scheduled triage cycle",
                    "Triage Status": "Scheduled for review",
                }
            )
        if item.meeting_request:
            rows.append(
                {
                    "Follow-up Type": "Meeting Request",
                    "Thread ID": item.thread_id,
                    "Subject": item.subject,
                    "Resurface Timing": "; ".join(item.meeting_request.proposed_slots),
                    "Triage Status": "Pending faculty slot approval",
                }
            )
    return rows


def response_time_metrics(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute lightweight response metrics from audit_log.jsonl timestamps."""
    approval_entries = [
        e for e in entries
        if "approve" in str(e.get("intent", "")).lower()
        or "send" in str(e.get("action", "")).lower()
    ]
    timestamps = []
    for entry in approval_entries:
        try:
            timestamps.append(datetime.datetime.fromisoformat(entry["timestamp"]))
        except Exception:
            pass

    if len(timestamps) < 2:
        return {
            "approved_reply_events": len(timestamps),
            "average_time_to_response_minutes": None,
            "metric_basis": "audit_log.jsonl approval/send timestamps (historical data accumulating)",
        }

    timestamps.sort()
    gaps = [
        (later - earlier).total_seconds() / 60.0
        for earlier, later in zip(timestamps, timestamps[1:])
    ]
    return {
        "approved_reply_events": len(timestamps),
        "average_time_to_response_minutes": round(sum(gaps) / len(gaps), 2),
        "metric_basis": "Average gap between approval/send audit events across runs",
    }


def render_empty_state(icon: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="saas-empty-state">
            <span class="saas-empty-icon">{icon}</span>
            <div class="saas-empty-title">{html.escape(title)}</div>
            <div class="saas-empty-desc">{html.escape(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def gmail_chip(label: str, tone: str = "neutral") -> str:
    color_class = tone if tone in {"urgent", "high", "medium", "low", "admin", "student", "collaborator", "vendor", "pending", "approved", "sent", "draft", "neutral", "tertiary"} else "neutral"
    return (
        f'<span class="gmail-chip {color_class}">{html.escape(str(label))}</span>'
    )


def dedupe_chips(chips: List[str]) -> List[str]:
    seen = set()
    unique: List[str] = []
    for chip in chips:
        if not chip:
            continue
        normalized = chip.strip()
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        unique.append(chip)
    return unique


def render_gmail_row(sender: str, subject: str, preview: str, chips: List[str], timestamp: str, unread: bool = False, details_html: Optional[str] = None, show_checkbox: bool = False) -> None:
    sender_class = "gmail-sender unread" if unread else "gmail-sender"
    clean_chips = dedupe_chips(chips)
    row_html = (
        f'<div class="gmail-row {"unread" if unread else ""}">'
        f'<div class="{sender_class}">{html.escape(sender)}</div>'
        f'<div class="gmail-subject">{html.escape(subject)}<span class="gmail-preview">{html.escape(preview)}</span></div>'
        f'<div class="gmail-chips">{"".join(clean_chips)}</div>'
        f'<div class="gmail-time">{html.escape(timestamp)}</div>'
        '</div>'
    )
    details_block = ""
    if details_html:
        details_block = f'<div class="gmail-details">{details_html}'
        if show_checkbox:
            details_block += '<label class="gmail-action-check"><input type="checkbox" /> Mark Confirmed</label>'
        details_block += '</div>'
    st.markdown(f'<details class="gmail-item"><summary class="gmail-summary">{row_html}</summary>{details_block}</details>', unsafe_allow_html=True)


# =============================================================================
# Card-Based Draft Reply Renderer
# =============================================================================

def render_draft_card(item, audit: AuditLogger) -> None:
    draft: DraftReply = item.draft_reply
    state = st.session_state.draft_states[draft.draft_id]
    current_status = state["status"]

    urgency_val = item.urgency.value.lower()
    status_val = current_status.lower()

    if status_val in ["draft", "pending_review", "edited"]:
        status_badge_class = "badge-pending"
        card_class = "saas-card theme-amber"
    elif status_val in ["approved", "sent"]:
        status_badge_class = "badge-approved"
        card_class = "saas-card theme-green"
    elif status_val == "discarded":
        status_badge_class = "badge-discarded"
        card_class = "saas-card"
    else:
        status_badge_class = "badge-draft"
        card_class = "saas-card"

    urgency_badge_class = f"badge-{urgency_val}" if urgency_val in ["urgent", "high", "medium", "low"] else "badge-low"

    with st.container():
        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="draft-card-header">
                    <div>
                        <div class="draft-subject">{html.escape(draft.subject)}</div>
                        <div class="draft-meta">
                            <strong>From:</strong> {html.escape(item.sender)} &nbsp;|&nbsp;
                            <strong>To:</strong> {html.escape(draft.recipient)} &nbsp;|&nbsp;
                            <strong>Thread:</strong> <code>{html.escape(draft.thread_id)}</code>
                        </div>
                    </div>
                    <div>
                        <span class="badge {urgency_badge_class}">{html.escape(item.urgency.value.upper())}</span>
                        <span class="badge {status_badge_class}">{html.escape(current_status.upper())}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_editor, col_meta = st.columns([7, 3])

        with col_editor:
            edited_body = st.text_area(
                "Proposed Draft Reply (Editable)",
                value=st.session_state.draft_bodies[draft.draft_id],
                key=f"body_{draft.draft_id}",
                height=190,
                label_visibility="visible",
            )
            st.session_state.draft_bodies[draft.draft_id] = edited_body

            # Intent-colored action buttons
            btn_col1, btn_col2, btn_col3 = st.columns([1.2, 1, 1])

            with btn_col1:
                if st.button("Approve & Send", key=f"approve_{draft.draft_id}", type="primary"):
                    guarded = draft.model_copy(
                        update={
                            "body": edited_body,
                            "status": ApprovalStatus.APPROVED,
                            "approved_by": "Mailbox Owner Dashboard",
                        }
                    )
                    try:
                        auth = GoogleAuthManager(
                            credentials_path=str(ROOT / "credentials.json"),
                            token_path=str(ROOT / "token.json"),
                        )
                        gmail = auth.get_gmail_service(interactive=False)
                        sent = send_email_guarded(
                            gmail_service=gmail,
                            draft=guarded,
                            approver="Mailbox Owner Dashboard",
                        )
                        state.update(
                            {
                                "status": "sent",
                                "sent_message_id": sent.get("id"),
                                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            }
                        )
                        audit.log(
                            agent="Dashboard",
                            intent="approve_and_send_draft",
                            action="send_email_guarded",
                            input_data={"draft_id": draft.draft_id, "thread_id": draft.thread_id},
                            result={"status": "sent", "message_id": sent.get("id")},
                        )
                        st.success(f"Dispatched via guarded approval. Message ID: {sent.get('id')}")
                        st.rerun()
                    except Exception as exc:
                        audit.log(
                            agent="Dashboard",
                            intent="approve_and_send_draft",
                            action="send_email_guarded_failed",
                            input_data={"draft_id": draft.draft_id, "thread_id": draft.thread_id},
                            result={"error": str(exc)},
                            guardrail_passed=False,
                        )
                        st.error(f"Send blocked by guardrail: {exc}")

            with btn_col2:
                if st.button("Save Changes", key=f"edit_{draft.draft_id}"):
                    state.update(
                        {
                            "status": "draft",
                            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
                    )
                    audit.log(
                        agent="Dashboard",
                        intent="edit_draft",
                        action="save_edit",
                        input_data={"draft_id": draft.draft_id},
                        result={"status": "draft"},
                    )
                    st.info("Draft modifications saved to session.")

            with btn_col3:
                if st.button("Discard", key=f"discard_{draft.draft_id}"):
                    state.update(
                        {
                            "status": "discarded",
                            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
                    )
                    audit.log(
                        agent="Dashboard",
                        intent="discard_draft",
                        action="discard",
                        input_data={"draft_id": draft.draft_id},
                        result={"status": "discarded"},
                    )
                    st.warning("Draft marked discarded.")
                    st.rerun()

        with col_meta:
            citations_list = "<br>".join([f"• {html.escape(c)}" for c in draft.citations]) if draft.citations else "None"
            st.markdown(
                f"""
                <div class="draft-meta-box">
                    <strong>Category:</strong> {html.escape(item.category.value.capitalize())}<br>
                    <strong>Template:</strong> <code>{html.escape(str(draft.template_used))}</code><br>
                    <strong>Urgency Score:</strong> {item.urgency_score}/100<br>
                    <strong>Rationale:</strong> {html.escape(item.rationale)}<br><br>
                    <strong>Evidence Citations:</strong><br>
                    {citations_list}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px dashed #E2E8F0;'>", unsafe_allow_html=True)


# =============================================================================
# Main Application
# =============================================================================

def main() -> None:
    st.set_page_config(
        page_title="Email Organizer Agent | Faculty Review",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject SaaS Custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ---------------- Sidebar Controls ----------------
    with st.sidebar:
        st.markdown("### Pipeline Configuration")
        st.caption("Governed Node Graph with bounded validation retry & MCP Connector.")

        max_results = st.slider(
            "Number of threads to fetch",
            min_value=5,
            max_value=50,
            value=20,
            step=5,
            help="Configures the connector inbox fetch budget with automated Gmail API pagination.",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("Run Full Triage Pass", type="primary", use_container_width=True)

        if run_btn:
            with st.spinner(f"Ingesting {max_results} threads, evaluating domain metrics, running graph..."):
                st.session_state.graph_result = build_graph_result(max_results=max_results)

        st.markdown("---")
        st.markdown("#### Workflow Overview")
        st.markdown(
            """
            - **Connector:** One trusted source surface for all inbox, history, and calendar reads.
            - **State Machine:** Ingest → Plan → Workers ⟲ Validate → Assemble → Gate → Publish
            - **Guardrails:** Approval gate required for mail dispatch; no silent send path.
            - **Audit:** Durable JSONL append-only with checkpoint visibility.
            """
        )

        st.markdown("#### Lab Progress")
        st.markdown(
            """
            <div class="review-guide">
                <h4>Chapter 3 coverage</h4>
                <ul>
                    <li>Phase A: Foundations (Labs 1–6)</li>
                    <li>Phase B: Orchestration (Labs 7–8)</li>
                    <li>Phase C: Reliability (Labs 9–11)</li>
                    <li>Phase D: Governance & capstone (Labs 12–14)</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Ensure baseline run exists
    if "graph_result" not in st.session_state:
        with st.spinner("Initializing pipeline and fetching initial inbox snapshot..."):
            st.session_state.graph_result = build_graph_result(max_results=max_results)

    result: GraphRunResult = st.session_state.graph_result
    ensure_state(result)

    audit = audit_logger()
    audit.log(
        agent="Dashboard",
        intent="dashboard_view",
        action="render",
        input_data={"run_id": result.run_id},
        result={"status": result.status, "source_backend": result.source_backend},
    )

    # ---------------- Hero Header ----------------
    backend_label = "Live Gmail API" if result.source_backend == "live_api" else "Benchmark Fixture"

    st.markdown(
        f"""
        <div class="saas-hero">
            <div>
                <h1 class="saas-hero-title">Email Organizer Agent</h1>
                <p class="saas-hero-subtitle">
                    Faculty Mailbox Review & Governed Approval Console &nbsp;•&nbsp; Run ID: <code>{html.escape(result.run_id)}</code>
                </p>
            </div>
            <div>
                <span class="saas-hero-badge">
                    Connected: {backend_label}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not result.triaged_inbox:
        st.error(result.error or "Pipeline error: No triaged inbox produced.")
        return

    st.markdown(
        """
        <div class="review-guide">
            <h4>How to review this queue</h4>
            <ul>
                <li>Use the triaged inbox to see which threads matter most by urgency and sender category.</li>
                <li>Review draft replies in the queue as faculty-approved output only; no content sends without the human gate.</li>
                <li>Check action items and follow-ups to capture concrete work, deadlines, and meeting requests.</li>
                <li>Use the audit trail to confirm the pipeline decisions and governance checks for every run.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    inbox = result.triaged_inbox
    drafts = [item for item in inbox.items if item.draft_reply]
    actions = action_rows(inbox)
    urgent_count = sum(1 for item in inbox.items if item.urgency.value in ["urgent", "high"])
    pending_approvals = sum(
        1 for d in drafts
        if d.draft_reply and st.session_state.draft_states.get(d.draft_reply.draft_id, {}).get("status") == "draft"
    )

    specialist_summary = getattr(result, "specialist_registry_summary", {}) or {}
    checked_live_items = specialist_summary.get("checked_live_items", 0)
    matched_specialist_items = specialist_summary.get("matched_specialist_items", 0)
    specialist_note = specialist_summary.get("note", "specialist registry not checked")

    st.markdown(
        f"""
        <div class="summary-bar">
            <span class="summary-pill"><strong>{len(inbox.items)}</strong> threads</span>
            <span class="summary-pill"><strong>{urgent_count}</strong> urgent</span>
            <span class="summary-pill"><strong>{pending_approvals}</strong> pending approval</span>
            <span class="summary-pill"><strong>{len(actions)}</strong> actions</span>
            <span class="summary-pill"><strong>Specialists</strong> checked {checked_live_items} / matched {matched_specialist_items}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(specialist_note)

    st.markdown(
        """
        <div class="insight-grid">
            <div class="insight-card">
                <span class="insight-label">Source</span>
                <strong>Live mailbox data</strong>
                <span>Inbox thread fetches and urgent content checks are driven from the connected source.</span>
            </div>
            <div class="insight-card">
                <span class="insight-label">Draft output</span>
                <strong>Faculty review queue</strong>
                <span>Drafts remain in review until the mailbox owner approves or edits them.</span>
            </div>
            <div class="insight-card">
                <span class="insight-label">Action tracking</span>
                <strong>Task + deadline list</strong>
                <span>Concrete action items and commitments are surfaced for the faculty owner.</span>
            </div>
            <div class="insight-card">
                <span class="insight-label">Governance</span>
                <strong>Audit + guardrail</strong>
                <span>Every run remains auditable and blocked from a silent send path.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    labs = [
        ("L01", "Agent vs Chatbot", "pass", "Clarify → plan → revise"),
        ("L02", "Tool-Using Agent", "pass", "Typed tools for data and metrics"),
        ("L03", "Skill Creation", "pass", "Reusable plan and formatting skills"),
        ("L04", "Memory & Retrieval", "pass", "State vs stored knowledge"),
        ("L05", "MCP Connector", "pass", "One connector for all sources"),
        ("L06", "Governed Runtime", "pass", "Audit, checkpoints, budgets"),
        ("L07", "Agentic Node Graph", "pass", "Graph pipeline and gate"),
        ("L08", "Parallel Swarm", "pass", "Fan-out/fan-in merge"),
        ("L09", "Deep Research", "pass", "Grounded evidence gate"),
        ("L10", "Ops Resilience", "pass", "Validate, diagnose, repair"),
        ("L11", "SDLC Factory", "pass", "Spec-to-tested-output"),
        ("L12", "Governance", "pass", "Approval, eval, rollback"),
        ("L13", "Specialists", "pass", "Domain specialists"),
        ("L14", "Capstone", "active", "Integrated team-owned system"),
    ]

    st.markdown("### Chapter 3 lab coverage")
    cards = "".join(
        f"<div class='lab-card {state}'><div class='lab-header'><span class='lab-no'>{lab_no}</span><span class='lab-badge'>{status}</span></div><div class='lab-title'>{title}</div><div class='lab-desc'>{desc}</div></div>"
        for lab_no, title, state, desc in labs
        for status in ["pass" if state == "pass" else "active" if state == "active" else "pending"]
    )
    st.markdown(f"<div class='labs-grid'>{cards}</div>", unsafe_allow_html=True)

    with st.expander("Color guide", expanded=False):
        st.markdown(
            """
            <div class="legend-guide">
                <span class="legend-item"><span class="legend-swatch navy"></span>Coordinator</span>
                <span class="legend-item"><span class="legend-swatch agent"></span>Agent</span>
                <span class="legend-item"><span class="legend-swatch amber"></span>Awaiting Approval</span>
                <span class="legend-item"><span class="legend-swatch green"></span>Published</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------- Tab Navigation ----------------
    tabs = st.tabs([
        "Triaged Inbox",
        "Draft-Reply Queue",
        "Action-Item List",
        "Follow-up Digest",
        "Live Audit Trail",
    ])

    # 1. Triaged Inbox Panel
    with tabs[0]:
        st.markdown("### Ranked Inbox Triage")
        st.caption("Prioritized threads with sender category, urgency, and actionability surfaced in a Gmail-like stack.")

        rows = triaged_rows(inbox)
        if rows:
            for row in rows:
                sender = row["Sender"]
                subject = row["Subject"]
                preview = row.get("Preview") or row["Subject"]
                full_body = row.get("Full Body") or row["Subject"]
                chips = [
                    gmail_chip(row["Urgency"].title(), tone=row["Urgency"].lower() if row["Urgency"].lower() in {"urgent", "high", "medium", "low"} else "neutral"),
                    gmail_chip(row["Category"], tone="tertiary" if row["Category"].lower() == "student" else "neutral"),
                ]
                details = (
                    f"<strong>Sender:</strong> {html.escape(sender)}<br>"
                    f"<strong>Subject:</strong> {html.escape(subject)}<br><br>"
                    f"<div style='white-space: pre-wrap;'>{html.escape(full_body)}</div>"
                )
                render_gmail_row(sender, subject, preview, chips, "Today", unread=True, details_html=details)
        else:
            render_empty_state("-", "Inbox Empty", "No threads found matching the search criteria.")

    # 2. Draft-Reply Queue Panel
    with tabs[1]:
        st.markdown("### Draft-Reply Approval Queue")
        st.caption("Draft responses stay in the queue until a faculty owner approves or edits them.")
        if not drafts:
            render_empty_state("-", "No Draft Replies Pending", "All actionable threads have been addressed or no vendor replies needed.")
        else:
            for item in drafts:
                render_draft_card(item, audit)

    # 3. Action-Item List Panel
    with tabs[2]:
        st.markdown("### Action Items & Commitments")
        st.caption("Concrete tasks, deadlines, and ownership extracted from the mailbox threads.")
        if actions:
            for row in actions:
                chips = [gmail_chip("Action", tone="pending")]
                deadline = row["Deadline"] if row["Deadline"] and row["Deadline"] != "None specified" else None
                if deadline:
                    chips.append(gmail_chip(deadline, tone="tertiary"))
                details = (
                    f"<strong>Thread:</strong> {html.escape(row['Thread ID'])}<br>"
                    f"<strong>Task:</strong> {html.escape(row['Task Description'])}<br>"
                    f"<strong>Owner:</strong> {html.escape(row['Assigned Owner'])}<br>"
                    f"<strong>Confirmed:</strong> {html.escape(row['Confirmed by Faculty'])}"
                )
                render_gmail_row(
                    "Faculty Mailbox Owner",
                    row["Task Description"],
                    "Confirm action required",
                    chips,
                    "",
                    unread=False,
                    details_html=details,
                    show_checkbox=True,
                )
        else:
            render_empty_state("-", "No Action Items", "No pending tasks or deadlines detected in current inbox threads.")

    # 4. Follow-up Digest Panel
    with tabs[3]:
        st.markdown("### Follow-up Digest & Response SLA Metrics")
        st.caption("Deferred replies and scheduling requests are grouped into a single review list.")

        rows_followup = followup_rows(inbox)
        if rows_followup:
            st.markdown('<div class="gmail-list">', unsafe_allow_html=True)
            for row in rows_followup:
                chips = [
                    gmail_chip(row["Follow-up Type"], tone="pending"),
                    gmail_chip("Review", tone="neutral"),
                ]
                details = (
                    f"<strong>Follow-up Type:</strong> {html.escape(row['Follow-up Type'])}<br>"
                    f"<strong>Resurface Timing:</strong> {html.escape(row['Resurface Timing'])}<br>"
                    f"<strong>Triage Status:</strong> {html.escape(row['Triage Status'])}"
                )
                render_gmail_row("Follow-up Review", row["Subject"], row["Resurface Timing"], chips, "Scheduled", unread=True, details_html=details)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            render_empty_state("-", "No Follow-up Items", "No reply-later flags or proposed meeting requests present.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Historical Response Timing Metrics")
        entries = audit.read_all()
        metrics = response_time_metrics(entries)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Approved/Dispatched Events", metrics["approved_reply_events"])
        with c2:
            avg = metrics["average_time_to_response_minutes"]
            st.metric("Average Turnaround Time", "N/A" if avg is None else f"{avg} min")
        st.caption(f"Basis: {metrics['metric_basis']}")

    # 5. Live Audit Trail Panel
    with tabs[4]:
        st.markdown("### Live Governed Audit Trail")
        st.caption("This log records the runtime decisions, payloads, checkpoints, and guardrail checks that keep the mailbox-owner approval model auditable.")

        entries = audit.read_all()
        if entries:
            display_entries = list(reversed(entries[-150:]))
            safe_df = safe_audit_dataframe(display_entries)
            st.dataframe(safe_df, width="stretch", hide_index=True)
        else:
            render_empty_state("-", "Audit Log Empty", "No runtime events recorded yet.")


if __name__ == "__main__":
    main()
