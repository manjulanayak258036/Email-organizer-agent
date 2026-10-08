"""Lab 4 Demonstration Script: Memory & Retrieval — State vs Stored.

Proves acceptance criteria from Chapter 3:
"Retrieval over the store + history with tag filters and embedding similarity.
Accept: For a given task, retrieval returns correctly-tagged candidates and similar prior items."

Enforces exact Chapter 3 pseudocode memory split:
  state.draft = candidate                              # short-term
  hits = memory.retrieve(store, tags)                  # long-term
  prior = memory.retrieve(history, embed(candidate), k=5)  # similarity

Guarantees anti-corruption:
  Short-term session draft mutations never pollute long-term store or historical archives.
"""

from __future__ import annotations
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.models import ApprovalStatus
from lab02_tools.tools import SAMPLE_FACULTY_THREADS
from lab04_memory.memory import MemoryManager, LongTermMemoryStore, SessionState
from lab04_memory.agent import RetrievalAgent


def main():
    print("=" * 75)
    print("LAB 4: Memory & Retrieval — State vs Stored Knowledge")
    print("=" * 75)

    memory_manager = MemoryManager()
    agent = RetrievalAgent(memory_manager=memory_manager)

    initial_store_len = len(memory_manager.long_term.store)
    initial_history_len = len(memory_manager.long_term.history)

    print(f"\n[Initial Knowledge Architecture]:")
    print(f"  Long-Term Reference Store items: {initial_store_len} (Policies, Syllabi, MOUs)")
    print(f"  Long-Term Historical Archives:   {initial_history_len} (Past email threads & faculty replies)")
    print(f"  Short-Term Session Draft:        {memory_manager.state.draft} (None at start)")

    # =========================================================================
    # TASK 1: Student Inquiry on CS401 Problem 3 (Cache Coherence & Office Hours)
    # =========================================================================
    print("\n" + "#" * 75)
    print("TASK 1: Student Query Retrieval — Cache Coherence & Office Hours")
    print("#" * 75)

    # Email thread: Sarah Lin asking about Problem 3 and Wednesday office hours
    thread_1 = SAMPLE_FACULTY_THREADS[2]  # th_003_student_office_hours
    print(f"\n[Incoming Task 1 Email Thread]:")
    print(f"  ID: {thread_1.thread_id}")
    print(f"  Subject: {thread_1.subject}")
    print(f"  Sender:  {thread_1.sender}")
    print(f"  Snippet: {thread_1.snippet}")

    task_1_tags = ["cs401", "office_hours"]
    print(f"\n[Retrieval Spec]: Store Tag Filter = {task_1_tags}, Similarity k = 3")

    result_1 = agent.process_email_candidate(
        thread=thread_1,
        retrieval_tags=task_1_tags,
        candidate_template="office_hours_confirmation",
        k_priors=3
    )

    # 1. Verify Short-Term Run State
    print("\n[1. Short-Term Run State Check]:")
    print(f"  state.draft.thread_id: {memory_manager.state.draft.thread_id}")
    print(f"  state.draft.status:    {memory_manager.state.draft.status.value}")
    assert memory_manager.state.draft.thread_id == thread_1.thread_id
    assert memory_manager.state.draft.status == ApprovalStatus.DRAFT

    # 2. Verify Tag-Based Store Retrieval
    print("\n[2. Long-Term Store Hits (Tag-Filtered)]: ")
    print(f"  Matches returned: {len(result_1.store_hits)}")
    for hit in result_1.store_hits:
        print(f"  - [{hit.item_id}] {hit.title}")
        print(f"    Tags: {hit.tags}")
        print(f"    Content preview: {hit.content[:85]}...")
    assert len(result_1.store_hits) >= 1
    assert any("cs401" in h.tags for h in result_1.store_hits)

    # 3. Verify Embedding Similarity Historical Retrieval
    print("\n[3. Historical Archive Hits (Embedding Cosine Similarity)]: ")
    for rank, p in enumerate(result_1.prior_history_hits, 1):
        print(f"  - Rank {rank} [Score: {p['similarity_score']:.4f}] {p['thread_id']}: {p['subject']}")
        if p["prior_faculty_reply"]:
            print(f"    Past Faculty Reply snippet: \"{p['prior_faculty_reply'][:80]}...\"")

    top_prior_1 = result_1.best_matching_prior
    assert top_prior_1 is not None
    assert top_prior_1["thread_id"] == "prior_th_101", f"Expected prior_th_101, got {top_prior_1['thread_id']}"
    assert top_prior_1["similarity_score"] > 0.30, "Expected significant similarity for cache coherence query"
    print(f"\n[ACCEPTANCE PASS - TASK 1]: Correctly returned tagged policy '{result_1.store_hits[0].title}' "
          f"and top similar prior thread '{top_prior_1['thread_id']}' (similarity: {top_prior_1['similarity_score']}).")

    # =========================================================================
    # TASK 2: Dean's Office Curriculum Review Deadline
    # =========================================================================
    print("\n" + "#" * 75)
    print("TASK 2: Admin Request Retrieval — Faculty Senate Curriculum Submission")
    print("#" * 75)

    thread_2 = SAMPLE_FACULTY_THREADS[1]  # th_002_dean_curriculum
    print(f"\n[Incoming Task 2 Email Thread]:")
    print(f"  ID: {thread_2.thread_id}")
    print(f"  Subject: {thread_2.subject}")
    print(f"  Sender:  {thread_2.sender}")
    print(f"  Snippet: {thread_2.snippet}")

    task_2_tags = ["senate", "curriculum", "deadline"]
    print(f"\n[Retrieval Spec]: Store Tag Filter = {task_2_tags}, Similarity k = 3")

    result_2 = agent.process_email_candidate(
        thread=thread_2,
        retrieval_tags=task_2_tags,
        candidate_template="admin_acknowledgement",
        k_priors=3
    )

    # 1. Verify Short-Term Run State Switched
    print("\n[1. Short-Term Run State Check]:")
    print(f"  state.draft.thread_id: {memory_manager.state.draft.thread_id}")
    assert memory_manager.state.draft.thread_id == thread_2.thread_id

    # 2. Verify Tag-Based Store Retrieval
    print("\n[2. Long-Term Store Hits (Tag-Filtered)]: ")
    for hit in result_2.store_hits:
        print(f"  - [{hit.item_id}] {hit.title}")
        print(f"    Tags: {hit.tags}")
    assert len(result_2.store_hits) >= 1
    assert any("senate" in h.tags for h in result_2.store_hits)

    # 3. Verify Embedding Similarity Historical Retrieval
    print("\n[3. Historical Archive Hits (Embedding Cosine Similarity)]: ")
    for rank, p in enumerate(result_2.prior_history_hits, 1):
        print(f"  - Rank {rank} [Score: {p['similarity_score']:.4f}] {p['thread_id']}: {p['subject']}")

    top_prior_2 = result_2.best_matching_prior
    assert top_prior_2 is not None
    assert top_prior_2["thread_id"] == "prior_th_103", f"Expected prior_th_103, got {top_prior_2['thread_id']}"
    assert top_prior_2["similarity_score"] > 0.30
    print(f"\n[ACCEPTANCE PASS - TASK 2]: Correctly returned tagged policy '{result_2.store_hits[0].title}' "
          f"and top similar prior thread '{top_prior_2['thread_id']}' (similarity: {top_prior_2['similarity_score']}).")

    # =========================================================================
    # TASK 3: PhD Thesis Defense Committee Sign-off
    # =========================================================================
    print("\n" + "#" * 75)
    print("TASK 3: Advising Request Retrieval — Thesis Committee Sign-off Deadline")
    print("#" * 75)

    thread_3 = SAMPLE_FACULTY_THREADS[0]  # th_001_grad_thesis
    task_3_tags = ["thesis", "deadline"]
    result_3 = agent.process_email_candidate(
        thread=thread_3,
        retrieval_tags=task_3_tags,
        candidate_template="thesis_advising_response",
        k_priors=3
    )

    top_prior_3 = result_3.best_matching_prior
    assert any("thesis" in h.tags for h in result_3.store_hits)
    assert top_prior_3["thread_id"] == "prior_th_102"
    print(f"[ACCEPTANCE PASS - TASK 3]: Correctly matched thesis policy and historical prior '{top_prior_3['thread_id']}'.")

    # =========================================================================
    # DIRECT PSEUDOCODE INTERFACE VERIFICATION
    # =========================================================================
    print("\n" + "-" * 75)
    print("DIRECT MEMORY SPLIT PSEUDOCODE VERIFICATION")
    print("-" * 75)
    print("  state.draft = candidate                              # short-term")
    print("  hits = memory.retrieve(store, tags)                  # long-term")
    print("  prior = memory.retrieve(history, embed(candidate), k=5)  # similarity\n")

    # Replicate exact pseudocode lines manually
    candidate = result_1.active_draft
    memory_manager.state.draft = candidate
    assert memory_manager.state.draft == candidate

    hits = memory_manager.retrieve("store", tags=["syllabus", "course"])
    assert len(hits) >= 1
    print(f"  -> Direct store retrieve returned {len(hits)} tagged items.")

    prior = memory_manager.retrieve("history", query=memory_manager.embed(candidate), k=5)
    assert len(prior) == 5
    print(f"  -> Direct history retrieve returned top-{len(prior)} similar items (top score: {prior[0][1]:.4f}).")

    # =========================================================================
    # PITFALL AVOIDANCE TEST: Run State vs Archive Conflation
    # =========================================================================
    print("\n" + "-" * 75)
    print("PITFALL AVOIDANCE VERIFICATION: Memory Partition Integrity")
    print("-" * 75)
    print("  Testing that short-term session mutations do not bleed into or corrupt long-term archives...")

    partition_valid = agent.verify_memory_partition(
        initial_store_count=initial_store_len,
        initial_history_count=initial_history_len
    )
    assert partition_valid, "Violation: Short-term run state leaked into long-term store or history!"
    print("  -> Session draft aggressively mutated with overwrite markers.")
    print("  -> Long-term store count:   UNCHANGED")
    print("  -> Long-term history count: UNCHANGED")
    print("  -> Historical baseline:     CORRUPTION-FREE")
    print("\n[ACCEPTANCE PASS - ISOLATION]: Run state and archived memory remain strictly segregated.")

    print("\n" + "=" * 75)
    print("ALL LAB 4 ACCEPTANCE CRITERIA SATISFIED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    main()
