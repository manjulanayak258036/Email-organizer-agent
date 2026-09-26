"""Lab 2: Tool-Using Agent — Call Data & Compute.

Implements Chapter 3 Lab 2:
- Reads inbox & threads via typed reader
- Reads contacts & prior replies via typed reader
- Calls domain calculator/checker
- Enforces:
    a = tool.read('the inbox & threads')
    b = tool.read('contacts & prior replies')
    v = tool.compute(a, b)
    assert v.valid
"""

from __future__ import annotations
from typing import Dict, Any, List
from lab02_tools.tools import (
    InboxReaderTool,
    ContactsPriorRepliesTool,
    UrgencyDomainCalculatorTool,
    ComputedDomainMetrics,
)
from core.models import EmailThread


class ToolUsingCoordinatorAgent:
    """Coordinator agent using typed tools for all data lookups and computations."""

    def __init__(
        self,
        inbox_tool: InboxReaderTool,
        contacts_tool: ContactsPriorRepliesTool,
        calculator_tool: UrgencyDomainCalculatorTool,
    ):
        self.inbox_tool = inbox_tool
        self.contacts_tool = contacts_tool
        self.calculator_tool = calculator_tool

    def run_tool_pipeline(self, query: str = "label:INBOX") -> Dict[str, Any]:
        """Executes the tool layer feeding the data agents."""
        # 1. Read inbox & threads via typed reader tool
        threads: List[EmailThread] = self.inbox_tool.read(query=query)

        # 2. Read contacts & prior replies via typed lookup tool
        contacts: List[Dict[str, Any]] = self.contacts_tool.read()

        # 3. Compute domain values through typed domain calculator
        computed_metrics: ComputedDomainMetrics = self.calculator_tool.compute(threads, contacts)

        # 4. Mandatory assertion per Lab 2 specification
        assert computed_metrics.valid, f"Validation failure in computed metrics: {computed_metrics.validation_notes}"

        # 5. Package verified results where every key number comes from tool compute
        return {
            "thread_count": computed_metrics.total_threads,
            "deadline_count": computed_metrics.detected_deadlines_count,
            "action_item_count": computed_metrics.detected_action_items_count,
            "sender_categories": computed_metrics.sender_category_counts,
            "urgency_tiers": computed_metrics.urgency_tier_counts,
            "per_thread_scores": computed_metrics.per_thread_scores,
            "threads": [t.model_dump() for t in threads],
            "valid": computed_metrics.valid,
        }
