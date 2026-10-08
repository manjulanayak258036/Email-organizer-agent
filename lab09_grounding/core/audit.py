"""Audit logging infrastructure for the Email Organizer Agent.

Maintains a persistent JSONL audit trail of every agent action, guardrail validation,
and human approval/edit/override decision.
"""

from __future__ import annotations
import json
import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class AuditLogger:
    def __init__(self, log_path: Optional[str] = None):
        if log_path is None:
            # Default to audit_log.jsonl in current working directory or project root
            log_path = "audit_log.jsonl"
        self.log_path = Path(log_path)
        # Ensure parent directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        agent: str,
        intent: str,
        action: str,
        input_data: Any = None,
        result: Any = None,
        guardrail_passed: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an action to the audit trail."""
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "agent": agent,
            "intent": intent,
            "action": action,
            "guardrail_passed": guardrail_passed,
            "input_summary": self._summarize(input_data),
            "result_summary": self._summarize(result),
            "metadata": metadata or {},
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return entry

    def _summarize(self, data: Any) -> Any:
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, dict):
            return {k: self._summarize(v) for k, v in list(data.items())[:10]}
        if isinstance(data, (list, tuple)):
            return [self._summarize(x) for x in data[:10]]
        if hasattr(data, "model_dump"):
            return data.model_dump()
        return str(data)[:200]

    def read_all(self) -> list[dict]:
        """Read all audit log entries."""
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries
