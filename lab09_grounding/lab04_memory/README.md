# Lab 4: Memory & Retrieval — State vs Stored Knowledge

## Goal
Separate short-term run state (the active session draft) from long-term stored knowledge (the reference store and historical archives), activating the **Retrieval Node** and laying the groundwork for evidence-grounded screening and validation.

## What It Adds
1. **Lightweight Local Vector Embedder (`LocalVectorEmbedder`)**:
   - Computes local TF-IDF vector representations and normalized cosine similarities in $[0.0, 1.0]$.
   - Zero external API keys or third-party service dependencies. Runs completely offline in pure Python.
2. **Long-Term Memory Store (`LongTermMemoryStore`)**:
   - **Reference Store (`store`)**: Contains faculty policies, course syllabi, university committee deadlines, and MOUs with metadata tags (`tags`).
   - **Historical Archives (`history`)**: Contains prior email thread exchanges and past faculty replies.
   - Provides dual retrieval modes:
     - **Tag-filtered retrieval**: `hits = memory.retrieve("store", tags=tags)`
     - **Embedding-similarity retrieval**: `prior = memory.retrieve("history", query=candidate_vec, k=5)`
3. **Short-Term Run State (`SessionState`)**:
   - Tracks ephemeral execution artifacts (`state.draft = candidate`, active thread ID, in-flight notes).
   - Strict memory partition: mutations to `state.draft` never alter or corrupt the underlying long-term baseline.
4. **Retrieval Agent (`RetrievalAgent`)**:
   - Executes the exact Chapter 3 pseudocode memory split:
     ```python
     state.draft = candidate                                  # short-term
     hits = memory.retrieve(store, tags)                      # long-term
     prior = memory.retrieve(history, embed(candidate), k=5)  # similarity
     ```

## Acceptance Criteria (Chapter 3 PDF)
> **Acceptance**: Retrieval over the store + history with tag filters and embedding similarity. For a given task, retrieval returns correctly-tagged candidates and similar prior items.

## Pitfall Avoided
> **Pitfall to avoid**: *Don't conflate run state with the archive — mixing them corrupts the baseline.*
> Verified by mutating short-term drafts aggressively and confirming zero data leakage into the reference store or historical replies.

## How to Run the Demo
```bash
python lab04_memory/demo_lab04.py
```

## Proof of Acceptance
When executing `demo_lab04.py`:
- **Task 1 (Student Query)**: Successfully matches `store_cs401_office_hours_policy` by tag (`cs401`) and ranks historical thread `prior_th_101` (cache coherence question) as the top similarity hit (> 0.40).
- **Task 2 (Senate / Dean Request)**: Successfully matches `store_senate_curriculum_timeline` by tag (`senate`, `curriculum`) and ranks historical thread `prior_th_103` (curriculum review notice) as the top similarity hit.
- **Task 3 (Thesis Committee Filing)**: Matches thesis defense policy and prior advising approval exchange `prior_th_102`.
- **Anti-Corruption Verification**: Ephemeral draft mutations in session state leave store and history count and contents 100% intact.
