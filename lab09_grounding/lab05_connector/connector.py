"""Lab 5: MCP-Style Connector — One Server for All Sources.

Implements the Chapter 3 Lab 5 specification:
- A single Connector object exposes every data source (Gmail, Calendar, Memory Store)
  through a uniform interface so no agent ever touches a source directly.
- Agents call connector.read() / connector.search() — the connector resolves the source,
  enforces authentication, and returns typed data.

connector.expose pseudocode (Chapter 3 spec):
    connector.expose("inbox",   read=gmail.threads,   search=gmail.search)
    connector.expose("calendar",read=calendar.events, search=calendar.search)
    connector.expose("store",   read=memory.store,    search=memory.retrieve)

Pitfall avoided: no agent should touch a source directly.
Source provenance is always declared in the response so callers know whether
live API or fixture data was used.
"""

from __future__ import annotations

import base64
import datetime
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

# Resolve project root so this module works whether imported or run directly
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.auth import GoogleAuthManager
from core.models import EmailMessage, EmailThread
from lab02_tools.tools import (
    SAMPLE_CONTACTS_AND_HISTORY,
    SAMPLE_FACULTY_THREADS,
    UrgencyDomainCalculatorTool,
)
from lab04_memory.memory import (
    BENCHMARK_HISTORY_ITEMS,
    BENCHMARK_STORE_ITEMS,
    LongTermMemoryStore,
)


# =====================================================================
# 1. TYPED RESPONSE ENVELOPE
# =====================================================================

class ConnectorResponse(BaseModel):
    """Uniform, typed response envelope returned by every connector call."""

    source_name: str = Field(description="Logical source name (inbox, calendar, store, history, contacts)")
    source_backend: str = Field(description="'live_api' when real data was used, 'fixture' when sample fallback was used")
    operation: str = Field(description="'read' or 'search'")
    query: Optional[str] = None
    items: List[Any] = Field(default_factory=list)
    item_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retrieved_at: str = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def __len__(self) -> int:
        return self.item_count


# =====================================================================
# 2. SOURCE DESCRIPTOR
# =====================================================================

class SourceDescriptor:
    """Holds the read and search callables for a single registered source."""

    def __init__(
        self,
        name: str,
        read_fn: Callable[..., ConnectorResponse],
        search_fn: Callable[..., ConnectorResponse],
    ):
        self.name = name
        self.read_fn = read_fn
        self.search_fn = search_fn


# =====================================================================
# 3. THE CONNECTOR
# =====================================================================

class MCPStyleConnector:
    """MCP-Style Connector — one server for all sources.

    Implements the Chapter 3 pseudocode:
        connector.expose("inbox",    read=gmail.threads,    search=gmail.search)
        connector.expose("calendar", read=calendar.events,  search=calendar.search)
        connector.expose("store",    read=memory.store,     search=memory.retrieve)

    All agents call connector.read(source, ...) or connector.search(source, ...).
    No agent touches a backing source directly.
    """

    def __init__(self, auth_manager: Optional[GoogleAuthManager] = None):
        self._sources: Dict[str, SourceDescriptor] = {}
        self._auth_manager = auth_manager
        self._memory_store = LongTermMemoryStore()
        self._calculator = UrgencyDomainCalculatorTool()

        # Wire every source at construction time (connector.expose calls)
        self._register_all_sources()

    # ------------------------------------------------------------------
    # Public connector.expose API
    # ------------------------------------------------------------------

    def expose(
        self,
        name: str,
        read: Callable[..., ConnectorResponse],
        search: Callable[..., ConnectorResponse],
    ) -> None:
        """Register a named source with its read and search callables.

        Exact Chapter 3 pseudocode interface:
            connector.expose(name, read=..., search=...)
        """
        self._sources[name] = SourceDescriptor(name=name, read_fn=read, search_fn=search)

    # ------------------------------------------------------------------
    # Public connector.read / connector.search API
    # ------------------------------------------------------------------

    def read(self, source: str, **kwargs) -> ConnectorResponse:
        """Read from a registered source. Raises KeyError for unknown sources."""
        descriptor = self._get_source(source)
        return descriptor.read_fn(**kwargs)

    def search(self, source: str, **kwargs) -> ConnectorResponse:
        """Search a registered source. Raises KeyError for unknown sources."""
        descriptor = self._get_source(source)
        return descriptor.search_fn(**kwargs)

    def list_sources(self) -> List[str]:
        """Return names of all registered sources."""
        return list(self._sources.keys())

    # ------------------------------------------------------------------
    # Internal wiring
    # ------------------------------------------------------------------

    def _get_source(self, name: str) -> SourceDescriptor:
        if name not in self._sources:
            raise KeyError(
                f"Unknown connector source '{name}'. "
                f"Registered sources: {self.list_sources()}"
            )
        return self._sources[name]

    def _register_all_sources(self) -> None:
        """Wire all sources via connector.expose — the canonical registration pattern."""
        self.expose(
            "inbox",
            read=self._gmail_read_threads,
            search=self._gmail_search_threads,
        )
        self.expose(
            "calendar",
            read=self._calendar_read_events,
            search=self._calendar_search_events,
        )
        self.expose(
            "store",
            read=self._memory_read_store,
            search=self._memory_search_store,
        )
        self.expose(
            "history",
            read=self._memory_read_history,
            search=self._memory_search_history,
        )
        self.expose(
            "contacts",
            read=self._contacts_read,
            search=self._contacts_search,
        )

    # ------------------------------------------------------------------
    # SOURCE BACKENDS — Gmail
    # ------------------------------------------------------------------

    def _gmail_read_threads(
        self,
        max_results: int = 10,
        query: str = "label:INBOX",
    ) -> ConnectorResponse:
        """Reads inbox threads. Uses live Gmail API when authenticated; falls back to fixture."""
        if self._auth_manager:
            try:
                service = self._auth_manager.get_gmail_service(interactive=False)
                thread_headers = []
                page_token = None
                remaining = max_results

                while remaining > 0:
                    batch_size = min(remaining, 50)
                    req_kwargs = {
                        "userId": "me",
                        "q": query,
                        "maxResults": batch_size,
                    }
                    if page_token:
                        req_kwargs["pageToken"] = page_token

                    resp = service.users().threads().list(**req_kwargs).execute()
                    batch_threads = resp.get("threads", [])
                    if not batch_threads:
                        break
                    thread_headers.extend(batch_threads)
                    remaining -= len(batch_threads)
                    page_token = resp.get("nextPageToken")
                    if not page_token:
                        break

                def _extract_body_text(payload_data: Dict[str, Any]) -> str:
                    if not payload_data:
                        return ""
                    if payload_data.get("mimeType") == "text/plain" and payload_data.get("body", {}).get("data"):
                        data = payload_data["body"]["data"]
                        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                    for part in payload_data.get("parts", []):
                        text = _extract_body_text(part)
                        if text:
                            return text
                    if payload_data.get("body", {}).get("data"):
                        data = payload_data["body"]["data"]
                        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                    return ""

                thread_headers = thread_headers[:max_results]
                threads: List[EmailThread] = []
                for th in thread_headers:
                    tdata = (
                        service.users()
                        .threads()
                        .get(userId="me", id=th["id"])
                        .execute()
                    )
                    subject = "(No Subject)"
                    sender = "Unknown"
                    snippet = tdata.get("snippet") or ""
                    messages = []
                    for msg in tdata.get("messages", []):
                        payload = msg.get("payload", {})
                        headers = {
                            h["name"].lower(): h["value"]
                            for h in payload.get("headers", [])
                        }
                        msg_subject = headers.get("subject", subject)
                        msg_sender = headers.get("from", sender)
                        subject = msg_subject
                        sender = msg_sender
                        msg_snippet = msg.get("snippet", "")
                        if not snippet and msg_snippet:
                            snippet = msg_snippet

                        body_text = _extract_body_text(payload) or msg_snippet

                        messages.append(
                            EmailMessage(
                                message_id=msg["id"],
                                sender=msg_sender,
                                recipient=headers.get("to", ""),
                                subject=msg_subject,
                                date=headers.get("date", ""),
                                snippet=msg_snippet,
                                body=body_text,
                            )
                        )
                    threads.append(
                        EmailThread(
                            thread_id=th["id"],
                            subject=subject,
                            sender=sender,
                            snippet=snippet or (messages[0].snippet if messages else ""),
                            messages=messages,
                        )
                    )

                if threads:
                    return ConnectorResponse(
                        source_name="inbox",
                        source_backend="live_api",
                        operation="read",
                        query=query,
                        items=threads,
                        item_count=len(threads),
                        metadata={
                            "gmail_query": query,
                            "authenticated_user": self._get_gmail_user(),
                        },
                    )
            except Exception as exc:
                print(
                    f"[Connector:inbox] Live Gmail API unavailable ({exc}). "
                    "Falling back to faculty benchmark fixture."
                )

        # Fixture fallback — explicitly labeled
        fixture_threads = SAMPLE_FACULTY_THREADS[:max_results]
        return ConnectorResponse(
            source_name="inbox",
            source_backend="fixture",
            operation="read",
            query=query,
            items=fixture_threads,
            item_count=len(fixture_threads),
            metadata={"fixture": "SAMPLE_FACULTY_THREADS", "reason": "no_live_auth_or_api_error"},
        )

    def _gmail_search_threads(
        self,
        query: str = "",
        max_results: int = 10,
    ) -> ConnectorResponse:
        """Searches Gmail using a query string."""
        return self._gmail_read_threads(max_results=max_results, query=query)

    def _get_gmail_user(self) -> str:
        try:
            service = self._auth_manager.get_gmail_service(interactive=False)
            return service.users().getProfile(userId="me").execute().get("emailAddress", "unknown")
        except Exception:
            return "unknown"

    # ------------------------------------------------------------------
    # SOURCE BACKENDS — Google Calendar
    # ------------------------------------------------------------------

    def _calendar_read_events(
        self,
        calendar_id: str = "primary",
        max_results: int = 10,
        time_min: Optional[str] = None,
    ) -> ConnectorResponse:
        """Reads upcoming calendar events. Returns structured dicts (Calendar has no domain model yet)."""
        if not time_min:
            time_min = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if self._auth_manager:
            try:
                service = self._auth_manager.get_calendar_service(interactive=False)
                resp = (
                    service.events()
                    .list(
                        calendarId=calendar_id,
                        maxResults=max_results,
                        singleEvents=True,
                        orderBy="startTime",
                        timeMin=time_min,
                    )
                    .execute()
                )
                events = resp.get("items", [])
                simplified = [
                    {
                        "event_id": e.get("id", ""),
                        "summary": e.get("summary", "(No Title)"),
                        "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", ""),
                        "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date", ""),
                        "status": e.get("status", ""),
                        "organizer": e.get("organizer", {}).get("email", ""),
                        "attendees": [
                            a.get("email") for a in e.get("attendees", [])
                        ],
                    }
                    for e in events
                ]
                return ConnectorResponse(
                    source_name="calendar",
                    source_backend="live_api",
                    operation="read",
                    query=f"calendarId={calendar_id}",
                    items=simplified,
                    item_count=len(simplified),
                    metadata={
                        "calendar_id": calendar_id,
                        "time_min": time_min,
                        "authenticated_user": self._get_gmail_user(),
                    },
                )
            except Exception as exc:
                print(
                    f"[Connector:calendar] Live Calendar API unavailable ({exc}). "
                    "Returning empty fixture."
                )

        # Calendar has no fixture benchmark — return empty labeled response
        return ConnectorResponse(
            source_name="calendar",
            source_backend="fixture",
            operation="read",
            query="",
            items=[],
            item_count=0,
            metadata={"fixture": "none", "reason": "no_live_auth_or_api_error"},
        )

    def _calendar_search_events(
        self,
        query: str = "",
        calendar_id: str = "primary",
        max_results: int = 10,
    ) -> ConnectorResponse:
        """Searches calendar events by free-text query (uses Google's q param)."""
        if self._auth_manager:
            try:
                time_min = datetime.datetime.now(datetime.timezone.utc).isoformat()
                service = self._auth_manager.get_calendar_service(interactive=False)
                resp = (
                    service.events()
                    .list(
                        calendarId=calendar_id,
                        q=query,
                        maxResults=max_results,
                        singleEvents=True,
                        orderBy="startTime",
                        timeMin=time_min,
                    )
                    .execute()
                )
                events = resp.get("items", [])
                simplified = [
                    {
                        "event_id": e.get("id", ""),
                        "summary": e.get("summary", "(No Title)"),
                        "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", ""),
                        "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date", ""),
                        "status": e.get("status", ""),
                    }
                    for e in events
                ]
                return ConnectorResponse(
                    source_name="calendar",
                    source_backend="live_api",
                    operation="search",
                    query=query,
                    items=simplified,
                    item_count=len(simplified),
                    metadata={"calendar_id": calendar_id, "search_query": query},
                )
            except Exception as exc:
                print(f"[Connector:calendar] Search unavailable ({exc}).")

        return ConnectorResponse(
            source_name="calendar",
            source_backend="fixture",
            operation="search",
            query=query,
            items=[],
            item_count=0,
            metadata={"fixture": "none", "reason": "no_live_auth_or_api_error"},
        )

    # ------------------------------------------------------------------
    # SOURCE BACKENDS — Memory / Knowledge Store
    # ------------------------------------------------------------------

    def _memory_read_store(
        self,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
    ) -> ConnectorResponse:
        """Reads reference store items, optionally filtered by tags or category."""
        items = list(self._memory_store.store)
        if tags:
            tag_set = {t.lower() for t in tags}
            items = [i for i in items if tag_set & {t.lower() for t in i.tags}]
        if category:
            items = [i for i in items if i.category == category]

        return ConnectorResponse(
            source_name="store",
            source_backend="fixture",
            operation="read",
            items=items,
            item_count=len(items),
            metadata={"filter_tags": tags, "filter_category": category},
        )

    def _memory_search_store(self, tags: Optional[List[str]] = None, **kwargs) -> ConnectorResponse:
        """Alias for tag-filtered store read (search by tags)."""
        return self._memory_read_store(tags=tags)

    def _memory_read_history(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> ConnectorResponse:
        """Reads historical email archive, optionally filtered by category."""
        items = list(self._memory_store.history)
        if category:
            items = [i for i in items if i.category == category]
        items = items[:limit]
        return ConnectorResponse(
            source_name="history",
            source_backend="fixture",
            operation="read",
            items=items,
            item_count=len(items),
            metadata={"filter_category": category},
        )

    def _memory_search_history(
        self,
        query: str = "",
        k: int = 5,
    ) -> ConnectorResponse:
        """Searches historical archive by embedding cosine similarity."""
        results = self._memory_store.retrieve_history_by_similarity(query=query, k=k)
        serialized = [
            {
                "history_id": item.history_id,
                "thread_id": item.thread_id,
                "subject": item.subject,
                "similarity_score": round(score, 4),
                "category": item.category,
                "faculty_reply_snippet": (item.faculty_reply or "")[:100],
            }
            for item, score in results
        ]
        return ConnectorResponse(
            source_name="history",
            source_backend="fixture",
            operation="search",
            query=query,
            items=serialized,
            item_count=len(serialized),
            metadata={"k": k, "embedding": "local_tfidf_cosine"},
        )

    # ------------------------------------------------------------------
    # SOURCE BACKENDS — Contacts
    # ------------------------------------------------------------------

    def _contacts_read(self, **kwargs) -> ConnectorResponse:
        """Reads known contact profiles and prior reply metadata."""
        return ConnectorResponse(
            source_name="contacts",
            source_backend="fixture",
            operation="read",
            items=SAMPLE_CONTACTS_AND_HISTORY,
            item_count=len(SAMPLE_CONTACTS_AND_HISTORY),
            metadata={"fixture": "SAMPLE_CONTACTS_AND_HISTORY"},
        )

    def _contacts_search(self, query: str = "", **kwargs) -> ConnectorResponse:
        """Searches contacts by email substring or name."""
        query_lower = query.lower()
        matches = [
            c for c in SAMPLE_CONTACTS_AND_HISTORY
            if query_lower in c.get("contact", "").lower()
            or query_lower in c.get("name", "").lower()
        ]
        return ConnectorResponse(
            source_name="contacts",
            source_backend="fixture",
            operation="search",
            query=query,
            items=matches,
            item_count=len(matches),
            metadata={"fixture": "SAMPLE_CONTACTS_AND_HISTORY"},
        )


# =====================================================================
# 4. FACTORY — shared singleton connector with live auth
# =====================================================================

def build_connector(
    credentials_path: str = "credentials.json",
    token_path: str = "token.json",
) -> MCPStyleConnector:
    """Build and return a fully wired MCPStyleConnector using live auth when available."""
    creds_file = Path(credentials_path)
    token_file = Path(token_path)

    auth_manager: Optional[GoogleAuthManager] = None
    if creds_file.exists() and token_file.exists():
        try:
            auth_manager = GoogleAuthManager(
                credentials_path=str(creds_file),
                token_path=str(token_file),
            )
            # Warm up — verify token is still valid (non-interactive)
            auth_manager.get_credentials(interactive=False)
        except Exception as exc:
            print(f"[Connector] Auth warm-up failed ({exc}). Connector will use fixtures.")
            auth_manager = None

    return MCPStyleConnector(auth_manager=auth_manager)
