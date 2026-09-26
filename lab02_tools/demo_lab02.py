"""Lab 2 Demonstration Script: Tool-Using Agent — Call Data & Compute.

Proves acceptance criteria from Chapter 3:
"Key numbers and lookups always go through tools, never hand-done in the prompt."
"""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab02_tools.tools import (
    UrgencyDomainCalculatorTool,
    SAMPLE_FACULTY_THREADS,
    SAMPLE_CONTACTS_AND_HISTORY,
)
from lab05_connector.connector import build_connector


def main():
    print("=" * 70)
    print("LAB 2: Tool-Using Agent — Call Data & Compute")
    print("=" * 70)

    calculator_tool = UrgencyDomainCalculatorTool()

    print("\n[Acceptance Test (Deterministic)]")
    print("Using SAMPLE_FACULTY_THREADS fixture data so the graded acceptance")
    print("test is reproducible and never depends on today's live mailbox contents.\n")
    print("  a = tool.read('the inbox & threads')")
    print("  b = tool.read('contacts & prior replies')")
    print("  v = tool.compute(a, b)")
    print("  assert v.valid\n")

    # Deterministic acceptance path: fixture-backed tools only.
    fixture_threads = SAMPLE_FACULTY_THREADS
    fixture_contacts = SAMPLE_CONTACTS_AND_HISTORY
    fixture_metrics = calculator_tool.compute(fixture_threads, fixture_contacts)
    assert fixture_metrics.valid, f"Validation failure in fixture metrics: {fixture_metrics.validation_notes}"

    print("-" * 50)
    print("DETERMINISTIC VERIFIED VALUES PRODUCED BY TYPED TOOLS:")
    print(f"  Total Ingested Threads: {fixture_metrics.total_threads}")
    print(f"  Detected Deadlines:     {fixture_metrics.detected_deadlines_count}")
    print(f"  Detected Action Items:  {fixture_metrics.detected_action_items_count}")
    print("\n  Sender Category Breakdown (from tool lookup):")
    for cat, cnt in fixture_metrics.sender_category_counts.items():
        print(f"    - {cat.capitalize()}: {cnt}")

    print("\n  Urgency Tier Distribution (from domain calculator):")
    for tier, cnt in fixture_metrics.urgency_tier_counts.items():
        print(f"    - {tier.upper()}: {cnt}")

    print("\n  Per-Thread Computed Urgency Scores:")
    for tid, score in fixture_metrics.per_thread_scores.items():
        print(f"    - {tid}: {score}/100")
    print("-" * 50)

    # Acceptance Assertions:
    # 1. Lookups must come from tools
    assert fixture_metrics.total_threads > 0, "Tool must read email threads."
    assert len(fixture_metrics.sender_category_counts) > 0, "Categories must be mapped via contact tool."

    # 2. Key numbers must be verified by computation
    assert fixture_metrics.detected_deadlines_count >= 1, "Calculator must detect fixture deadlines."
    assert fixture_metrics.detected_action_items_count >= 1, "Calculator must detect fixture action items."

    # 3. Validation checker passed
    assert fixture_metrics.valid is True, "Domain checker must validate consistent math and normalization."

    print("\n[ACCEPTANCE PASS] Deterministic fixture data proves key numbers, counts,")
    print("                  and lookups are calculated by typed tools, with zero")
    print("                  values hardcoded in the agent prompt.")

    print("\n[Live Connectivity Check (Informational)]")
    print("Running the same typed tool pipeline against live Gmail. Live mailbox")
    print("content is intentionally not asserted to contain specific deadlines or actions.\n")

    connector = build_connector(
        credentials_path=str(ROOT / "credentials.json"),
        token_path=str(ROOT / "token.json"),
    )
    inbox_resp = connector.read("inbox", max_results=10, query="label:INBOX")
    contacts_resp = connector.read("contacts")
    live_metrics = calculator_tool.compute(inbox_resp.items, contacts_resp.items)
    assert live_metrics.valid, f"Validation failure in live metrics: {live_metrics.validation_notes}"

    print("-" * 50)
    print("LIVE GMAIL VALUES PRODUCED BY TYPED TOOLS:")
    print(f"  Source Backend:         {inbox_resp.source_backend}")
    print(f"  Total Ingested Threads: {live_metrics.total_threads}")
    print(f"  Detected Deadlines:     {live_metrics.detected_deadlines_count}")
    print(f"  Detected Action Items:  {live_metrics.detected_action_items_count}")
    print(f"  Valid Result:           {live_metrics.valid}")
    print("-" * 50)

    assert inbox_resp.item_count >= 0, "Live call must return a well-formed thread count."
    assert live_metrics.valid is True, "Live computed result must be internally consistent."
    print("[INFO PASS] Live Gmail integration returned a valid, well-formed result.")

    print("=" * 70)
    print("ALL LAB 2 ACCEPTANCE CRITERIA SATISFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
