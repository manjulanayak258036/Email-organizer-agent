# Lab 5: MCP-Style Connector

## Purpose

Implements the Chapter 3 "Lab 5 — MCP-Style Connector" specification:
> *"One server for all sources"* — a single `MCPStyleConnector` object exposes every data
> source through a uniform interface so **no agent ever touches a source directly**.

## Key Design

```python
# connector.expose pseudocode (Chapter 3 spec)
connector.expose("inbox",    read=gmail.threads,    search=gmail.search)
connector.expose("calendar", read=calendar.events,  search=calendar.search)
connector.expose("store",    read=memory.store,     search=memory.retrieve)
connector.expose("history",  read=memory.history,   search=memory.similarity)
connector.expose("contacts", read=contacts.list,    search=contacts.filter)
```

All agents call `connector.read(source, ...)` or `connector.search(source, ...)`.  
The connector resolves the backend, enforces authentication, and always declares
provenance in the typed `ConnectorResponse` envelope (`source_backend='live_api'` or `'fixture'`).

## Pitfall Avoided

> ❌ Agents calling Gmail / Calendar / memory stores directly.  
> ✅ All data access goes through the connector; swapping a source needs no agent change.

This is proven in Step 9 of the demo: the same `connector.read('inbox')` call
returns live data **or** fixture data depending on which connector instance is used —
with zero changes to the calling agent code.

## Source Provenance

Every `ConnectorResponse` declares `source_backend`:
- `'live_api'` — real Google API data (Gmail, Calendar)
- `'fixture'` — sample benchmark data (store, history, contacts, or API fallback)

Never silent substitution: the fallback is always labeled.

## Files

| File | Description |
|------|-------------|
| `connector.py` | Core `MCPStyleConnector`, `ConnectorResponse`, `SourceDescriptor`, `build_connector()` |
| `demo_lab05.py` | 9-step acceptance script verifying all criteria |
| `__init__.py` | Package exports |

## Running

```bash
python lab05_connector/demo_lab05.py
```

Requires `credentials.json` + `token.json` in the project root for live Gmail/Calendar access.
Falls back to fixture data when credentials are absent.

## Acceptance Results

| Step | Check | Result |
|------|-------|--------|
| 1 | `connector.expose()` for all 5 sources | ✅ PASS |
| 2 | Live Gmail inbox read (`live_api`) | ✅ PASS — 5 real threads |
| 3 | Gmail search via connector | ✅ PASS — 5 reminder/notice threads |
| 4 | Live Calendar read (`live_api`) | ✅ PASS — 0 upcoming events |
| 5 | Policy store tag-filtered read | ✅ PASS — 3 policy items |
| 6 | History TF-IDF similarity search | ✅ PASS — 3 ranked priors |
| 7 | Contacts read + search | ✅ PASS — 5 contacts |
| 8 | Labs 2–4 patterns routed through connector | ✅ PASS |
| 9 | Source swap — zero agent code changes | ✅ PASS |
