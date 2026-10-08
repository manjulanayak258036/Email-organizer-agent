"""Lab 8 acceptance script: parallel swimlane triage with plan-alignment merge."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab02_tools.tools import SAMPLE_FACULTY_THREADS
from lab08_parallel_swarm.agent import ALIGNMENT_SCORE_MAX, run_parallel_swarm


def main() -> None:
    print("=" * 75)
    print("LAB 8: Parallel Swarm - merge-by-alignment triage")
    print("=" * 75)
    print(f"Alignment scale: 0..{ALIGNMENT_SCORE_MAX} ({ALIGNMENT_SCORE_MAX}=best plan fit; 0=weakest fit)")
    print("Merge rule: keep the single highest alignment candidate per thread ID; do not pick the 'nicest' result if it drops coverage.")

    start = time.perf_counter()
    parallel_result = run_parallel_swarm(SAMPLE_FACULTY_THREADS, parallel=True)
    parallel_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    sequential_result = run_parallel_swarm(SAMPLE_FACULTY_THREADS, parallel=False)
    sequential_elapsed = time.perf_counter() - start

    print(f"Parallel elapsed: {parallel_elapsed:.4f}s")
    print(f"Sequential elapsed: {sequential_elapsed:.4f}s")
    print(f"Faster: {'parallel' if parallel_elapsed < sequential_elapsed else 'sequential'}")

    print("\nMerged items:")
    for item in parallel_result["items"]:
        print(f"- {item['subject']} | category={item['category']} | urgency={item['urgency']} | alignment={item['alignment_score']}")

    print("\nMerge trace:")
    for trace in parallel_result["merge_trace"][:5]:
        print(f"- {trace['thread_id']} -> selected={trace['selected_subject']} | score={trace['selected_alignment']} | kept_by_alignment={trace['kept_by_alignment']}")

    print(f"\nAverage alignment: {parallel_result['average_alignment']}")
    print(f"Alignment range: {parallel_result['alignment_range']}")

    assert parallel_result["merged_count"] == len(SAMPLE_FACULTY_THREADS)
    assert sequential_result["merged_count"] == len(SAMPLE_FACULTY_THREADS)
    assert parallel_result["average_alignment"] >= 0
    assert parallel_result["average_alignment"] <= ALIGNMENT_SCORE_MAX
    assert all(item["thread_id"] for item in parallel_result["items"])
    assert parallel_elapsed < sequential_elapsed, "Parallel run is required to be faster than sequential baseline for acceptance."
    print("\n[ACCEPTANCE PASS] Parallel threads were processed and merged by plan alignment; the parallel wall-clock time is lower than the sequential baseline.")


if __name__ == "__main__":
    main()
