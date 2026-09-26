"""Lab 7 Demonstration Script: Agentic Node Graph.

Proves the Chapter 3 acceptance criteria:
"One command yields a validated triaged inbox with draft replies draft end to end."

Also proves the stated pitfall is avoided:
"Bound the retry edge - an unbounded regenerate loop can spin forever."
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab07_node_graph.graph import AgenticNodeGraph


def print_trace(label: str, result) -> None:
    print("\n" + "-" * 75)
    print(label)
    print("-" * 75)
    print(f"Run ID:          {result.run_id}")
    print(f"Status:          {result.status}")
    print(f"Source backend:  {result.source_backend}")
    print(f"Attempts used:   {result.attempts_used} (max retries={result.max_retries})")
    if result.validation_report:
        print(f"Validation pass: {result.validation_report.passed}")
        print(f"Validation errs: {result.validation_report.errors}")
    print(f"Retry events:    {result.retry_events}")
    if result.triaged_inbox:
        drafts = sum(1 for item in result.triaged_inbox.items if item.draft_reply)
        actions = sum(len(item.action_items) for item in result.triaged_inbox.items)
        print(f"Triaged items:   {len(result.triaged_inbox.items)}")
        print(f"Draft replies:   {drafts}")
        print(f"Action items:    {actions}")
        print(f"Inbox status:    {result.triaged_inbox.status.value}")

    print("\nGraph node trace:")
    for step in result.graph_trace:
        print(
            f"  - {step['step_id']}: {step['status']} "
            f"(approval={step['approval_status']}, budget={step['budget_used']})"
        )


def main() -> None:
    print("=" * 75)
    print("LAB 7: Agentic Node Graph - the full pipeline")
    print("=" * 75)
    print("Topology:")
    print("  graph.chain(ingest -> plan -> workers -> validate)")
    print("  graph.edge(validate --fail--> workers)   # bounded retry")
    print("  graph.edge(validate --pass--> assemble -> gate -> publish)")

    print("\n[Part 1] End-to-end graph with one injected validation failure")
    graph = AgenticNodeGraph(max_retries=2)
    result = graph.run(
        max_results=5,
        inject_validation_failure_once=True,
    )
    print_trace("END-TO-END VALIDATED RUN", result)

    assert result.status == "published_review_artifact"
    assert result.validation_report is not None and result.validation_report.passed is True
    assert result.attempts_used == 2, "Injected first failure should require exactly one retry."
    assert len(result.retry_events) == 1
    assert result.triaged_inbox is not None
    assert result.triaged_inbox.items
    assert any(item.draft_reply for item in result.triaged_inbox.items)
    print("\n[ACCEPTANCE PASS] One command produced a validated triaged inbox with draft replies end to end.")
    print("[ACCEPTANCE PASS] validate --fail--> workers back-edge retried once, then passed.")

    print("\n[Part 2] Forced validation failure to prove bounded retry exhaustion")
    failing_graph = AgenticNodeGraph(max_retries=2)
    failing_result = failing_graph.run(
        max_results=5,
        force_validation_failure=True,
    )
    print_trace("BOUNDED RETRY EXHAUSTION RUN", failing_result)

    assert failing_result.status == "failed_validation"
    assert failing_result.attempts_used == 3, "max_retries=2 means 3 total attempts."
    assert "bounded retry exhausted" in failing_result.retry_events[-1]
    print("\n[ACCEPTANCE PASS] Forced failure stopped after the fixed retry budget; no infinite loop.")

    print("\n" + "=" * 75)
    print("ALL LAB 7 ACCEPTANCE CRITERIA SATISFIED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
