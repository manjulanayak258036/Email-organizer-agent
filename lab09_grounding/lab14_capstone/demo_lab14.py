"""Lab 14 acceptance demo: integrated capstone worklet."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab14_capstone.agent import CapstoneWorklet


def main() -> None:
    print("=" * 80)
    print("LAB 14: Capstone - Team-Owned System")
    print("=" * 80)
    print("Command to run: python lab14_capstone/demo_lab14.py")

    request = {
        "query": "label:INBOX",
        "max_results": 20,
    }

    worklet = CapstoneWorklet(mailbox_owner="faculty_owner")
    result = worklet.run(request)
    specialist_summary = result["artifact"]["specialist_registry_summary"]
    print("\n-- capstone result --")
    print(result)
    print(f"\n-- specialist registry summary --")
    print(specialist_summary)

    assert result["status"] == "approved_and_ready_for_dashboard"
    assert result["artifact"]["approval_contract"]["rule"]
    assert "standard approval gate" in result["artifact"]["approval_contract"]["note"].lower()
    assert specialist_summary["checked_live_items"] >= 1
    assert "checked" in specialist_summary["note"].lower()

    print("\n[ACCEPTANCE PASS] The worklet integrated the connector, runtime, graph, governance, and specialist registry against live inbox data in one run, with the registry summary showing exactly how many real items were checked.")


if __name__ == "__main__":
    main()
