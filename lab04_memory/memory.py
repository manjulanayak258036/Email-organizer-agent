"""Lab 4: Memory & Retrieval — State vs Stored Knowledge.

Implements the Lab 4 Chapter 3 specification:
- Separates short-term run state (session/draft) from long-term stored knowledge (store + history).
- Implements the memory split:
    state.draft = candidate                           # short-term
    hits = memory.retrieve(store, tags)               # long-term (tag-filtered)
    prior = memory.retrieve(history, embed(candidate), k=5)  # similarity (local TF-IDF cosine similarity)
- Prevents corrupting the historical baseline with ephemeral session modifications.
"""

from __future__ import annotations
import re
import math
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from pydantic import BaseModel, Field

from core.models import DraftReply, EmailThread, ApprovalStatus


# =====================================================================
# 1. LIGHTWEIGHT LOCAL EMBEDDER (TF-IDF Cosine Similarity)
# =====================================================================

class LocalVectorEmbedder:
    """Lightweight, deterministic local text embedder and cosine similarity engine.
    
    Zero external API key dependencies. Computes TF-IDF vector representations 
    and cosine similarity rankings over local text documents.
    """

    STOPWORDS: Set[str] = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
        "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
        "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
        "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
        "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
        "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
        "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
        "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
        "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
        "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
        "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
        "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll",
        "they're", "they've", "this", "those", "through", "to", "too", "under", "until",
        "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
        "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
        "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
        "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours"
    }

    def tokenize(self, text: str) -> List[str]:
        """Extracts normalized alphanumeric word tokens excluding common stopwords."""
        words = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
        return [w for w in words if w not in self.STOPWORDS]

    def compute_idf(self, documents: List[str]) -> Dict[str, float]:
        """Computes inverse document frequencies (IDF) across a document collection."""
        num_docs = max(1, len(documents))
        doc_freq: Counter = Counter()

        for doc in documents:
            unique_terms = set(self.tokenize(doc))
            for term in unique_terms:
                doc_freq[term] += 1

        idf: Dict[str, float] = {}
        for term, freq in doc_freq.items():
            # Smooth IDF: ln(1 + (N / (1 + df))) + 1
            idf[term] = math.log(1.0 + (num_docs / (1.0 + freq))) + 1.0
        return idf

    def embed(self, text: str, idf: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Computes a sparse TF-IDF embedding vector for the given text."""
        tokens = self.tokenize(text)
        if not tokens:
            return {}

        tf_counts = Counter(tokens)
        total_tokens = len(tokens)

        vector: Dict[str, float] = {}
        for term, count in tf_counts.items():
            tf = count / total_tokens
            weight = idf.get(term, 1.0) if idf else 1.0
            vector[term] = tf * weight

        # L2 Normalize
        norm = math.sqrt(sum(val * val for val in vector.values()))
        if norm > 0.0:
            for term in vector:
                vector[term] /= norm

        return vector

    def cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """Computes cosine similarity between two normalized sparse vectors in [0.0, 1.0]."""
        if not vec_a or not vec_b:
            return 0.0

        # Dot product of common terms (since vectors are already unit-norm)
        common_terms = set(vec_a.keys()) & set(vec_b.keys())
        sim = sum(vec_a[t] * vec_b[t] for t in common_terms)
        return max(0.0, min(1.0, sim))


# =====================================================================
# 2. LONG-TERM STORE & HISTORY DATA SCHEMAS
# =====================================================================

class StoreItem(BaseModel):
    """An item in the long-term reference store (e.g. syllabus, university policy, templates)."""
    item_id: str
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    category: str = "general"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HistoryItem(BaseModel):
    """An archived historical email thread exchange with prior faculty replies."""
    history_id: str
    thread_id: str
    subject: str
    sender: str
    snippet: str
    body: str
    faculty_reply: Optional[str] = None
    category: str
    tags: List[str] = Field(default_factory=list)
    timestamp: str


# Baseline faculty long-term reference store (static policies, syllabus, templates)
BENCHMARK_STORE_ITEMS: List[StoreItem] = [
    StoreItem(
        item_id="store_cs401_office_hours_policy",
        title="CS401 Course Syllabus & Office Hours Policy",
        content=(
            "CS401 Computer Architecture: Dr. Vance holds weekly office hours on Wednesdays from 2:00 PM to 4:00 PM "
            "in Hall 412 and via Zoom. Students asking homework or Assignment 2 questions should attend office hours "
            "or review posted lecture notes on cache coherence protocols (MESI / MSI)."
        ),
        tags=["cs401", "student", "office_hours", "syllabus", "course"],
        category="student"
    ),
    StoreItem(
        item_id="store_grad_thesis_defense_policy",
        title="Graduate School PhD Thesis Defense Committee Filing Policy",
        content=(
            "Graduate School Directive: Signed thesis defense committee approval forms must be signed by the principal "
            "adviser and submitted to the Graduate School office at least 10 business days before the scheduled defense. "
            "The hard deadline for current semester candidates is Friday at 5:00 PM."
        ),
        tags=["thesis", "grad", "phd", "advising", "deadline", "student"],
        category="student"
    ),
    StoreItem(
        item_id="store_senate_curriculum_timeline",
        title="Academic Senate Curriculum Committee Deadlines & Guidelines",
        content=(
            "Faculty Senate Curriculum Review: Departmental representatives must submit revised course syllabi, "
            "lab safety compliance checklists, and prerequisite updates through the Senate portal by Wednesday at 3:00 PM. "
            "Late submissions are held over until the subsequent academic cycle."
        ),
        tags=["senate", "curriculum", "admin", "deadline", "governance"],
        category="admin"
    ),
    StoreItem(
        item_id="store_quantum_consortium_mou",
        title="Quantum Computing Research Consortium Publication Guidelines",
        content=(
            "Multi-institution Quantum Simulation Project: Joint manuscripts covering benchmark figures and error-mitigation "
            "algorithms must undergo reciprocal co-investigator review before arXiv posting or journal submission. "
            "Dr. Reed and Dr. Vance serve as co-corresponding authors."
        ),
        tags=["research", "quantum", "collaborator", "manuscript", "grant"],
        category="collaborator"
    ),
    StoreItem(
        item_id="store_it_procurement_policy",
        title="University IT & Hardware Procurement Regulations",
        content=(
            "Commercial software and server hardware purchases must be routed via central purchasing with an approved PO. "
            "Cold outreach, unsolicited vendor discounts, and marketing promotions do not constitute formal university bids."
        ),
        tags=["vendor", "procurement", "hardware", "policy"],
        category="vendor"
    ),
]


# Baseline faculty long-term historical archive (prior email threads and past sent replies)
BENCHMARK_HISTORY_ITEMS: List[HistoryItem] = [
    HistoryItem(
        history_id="hist_001_cache_coherence",
        thread_id="prior_th_101",
        subject="CS401: Question on Problem 3 cache coherence transitions",
        sender="prior.student@student.university.edu",
        snippet="Professor Vance, how does the Invalid state transition during write misses?",
        body=(
            "Professor Vance, I am working through Problem 3 on Assignment 2. In the MESI protocol, when a processor writes "
            "to a line in Invalid state, does it issue a BusRdX or BusUpgr? Could we discuss during Wednesday office hours?"
        ),
        faculty_reply=(
            "Hello, when the line is in Invalid state, the processor must issue a BusRdX (Read with Intent to Modify) to fetch "
            "the line and invalidate other caches. I will be in office hours on Wednesday at 2:30 PM if you want to walk through "
            "the timing diagram together."
        ),
        category="student",
        tags=["cs401", "assignment", "cache", "office_hours", "student"],
        timestamp="2026-03-12T14:10:00Z"
    ),
    HistoryItem(
        history_id="hist_002_thesis_committee_form",
        thread_id="prior_th_102",
        subject="PhD Defense: Committee Form Signature Request",
        sender="alex.turner@cs.university.edu",
        snippet="Dr. Vance, attached is the committee form for initial sign-off before Friday deadline...",
        body=(
            "Dr. Vance, following up on our advising discussion last week, here is the official Graduate School thesis committee "
            "form. The deadline for filing with the dean of graduate studies is this Friday at 5:00 PM."
        ),
        faculty_reply=(
            "Dear Alex, I reviewed the form and the committee roster looks complete. I have electronically signed and approved it. "
            "Please confirm once the graduate school portal acknowledges your receipt."
        ),
        category="student",
        tags=["thesis", "phd", "committee", "deadline", "student"],
        timestamp="2026-04-05T09:30:00Z"
    ),
    HistoryItem(
        history_id="hist_003_senate_curriculum_review",
        thread_id="prior_th_103",
        subject="Senate Notice: Syllabus updates deadline due tomorrow",
        sender="dean_academic@university.edu",
        snippet="Deans & Chairs: Reminder that all revised course syllabi must be uploaded by tomorrow 3 PM...",
        body=(
            "Deans and Department Chairs, please remind faculty that curriculum changes and course syllabi updates must be "
            "submitted to the Senate portal before Wednesday 3:00 PM."
        ),
        faculty_reply=(
            "Dear Dean's Office, the CS Department curriculum committee has finalized our syllabus updates and lab checklists. "
            "They will be uploaded to the portal ahead of tomorrow's 3:00 PM deadline."
        ),
        category="admin",
        tags=["senate", "curriculum", "deadline", "admin"],
        timestamp="2026-02-18T10:00:00Z"
    ),
    HistoryItem(
        history_id="hist_004_quantum_draft_exchange",
        thread_id="prior_th_104",
        subject="Joint manuscript: Section 4 benchmark figures updated",
        sender="dr.marcus.reed@partner-lab.org",
        snippet="Eleanor, I uploaded the new benchmark figures for quantum simulator scaling...",
        body=(
            "Eleanor, I pushed our latest quantum benchmark numbers to Section 4. When your schedule permits, please take a look "
            "at the error scaling plots and let me know if the narrative aligns with our experimental findings."
        ),
        faculty_reply=(
            "Hi Marcus, I reviewed Section 4 and the scaling curves look compelling. I made minor edits to the noise mitigation "
            "discussion. Let's aim to polish Section 5 by next week."
        ),
        category="collaborator",
        tags=["research", "quantum", "manuscript", "benchmarks", "collaborator"],
        timestamp="2026-05-14T16:45:00Z"
    ),
    HistoryItem(
        history_id="hist_005_vendor_server_pitch",
        thread_id="prior_th_105",
        subject="Exclusive academic discounts on rack servers",
        sender="sales@techserver-direct.com",
        snippet="Special compute node sale ends Friday...",
        body="Exclusive end-of-quarter hardware discounts on server racks for university research labs. Click here to speak with sales.",
        faculty_reply=None,
        category="vendor",
        tags=["vendor", "sales", "unsolicited"],
        timestamp="2026-01-20T11:15:00Z"
    ),
]


# =====================================================================
# 3. SHORT-TERM RUN STATE VS LONG-TERM MEMORY STORE
# =====================================================================

class SessionState(BaseModel):
    """Short-term, ephemeral run state for the active agent triage cycle.
    
    Implements: state.draft = candidate
    Isolated from long-term memory. Mutations here NEVER modify store or history.
    """
    session_id: str
    draft: Optional[DraftReply] = None
    active_thread_id: Optional[str] = None
    active_candidate_data: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
    step_history: List[str] = Field(default_factory=list)

    def set_draft(self, candidate: DraftReply) -> None:
        """Sets the active candidate draft in short-term run state."""
        self.draft = candidate
        self.active_thread_id = candidate.thread_id
        self.step_history.append(f"Set draft for thread {candidate.thread_id}")


class LongTermMemoryStore:
    """Long-term reference knowledge store and historical archives.
    
    Maintains:
    1. 'store': Reference policies, syllabus, templates.
    2. 'history': Prior email thread history and past faculty replies.
    
    Provides tag-based and similarity-based retrieval.
    """

    def __init__(
        self,
        store_items: Optional[List[StoreItem]] = None,
        history_items: Optional[List[HistoryItem]] = None,
        embedder: Optional[LocalVectorEmbedder] = None
    ):
        self.store: List[StoreItem] = store_items or list(BENCHMARK_STORE_ITEMS)
        self.history: List[HistoryItem] = history_items or list(BENCHMARK_HISTORY_ITEMS)
        self.embedder = embedder or LocalVectorEmbedder()

        # Precompute IDF over all historical thread texts
        corpus = [f"{h.subject} {h.snippet} {h.body} {h.faculty_reply or ''}" for h in self.history]
        self.idf = self.embedder.compute_idf(corpus)

        # Precompute unit embeddings for history items
        self.history_embeddings: List[Dict[str, float]] = [
            self.embedder.embed(f"{h.subject} {h.snippet} {h.body} {h.faculty_reply or ''}", self.idf)
            for h in self.history
        ]

    def add_store_item(self, item: StoreItem) -> None:
        self.store.append(item)

    def add_history_item(self, item: HistoryItem) -> None:
        self.history.append(item)
        full_text = f"{item.subject} {item.snippet} {item.body} {item.faculty_reply or ''}"
        self.history_embeddings.append(self.embedder.embed(full_text, self.idf))

    def retrieve_store_by_tags(self, tags: List[str], match_all: bool = False) -> List[StoreItem]:
        """Retrieves items from the reference store matching tag filters.
        
        Implements: hits = retrieve(store, tags)
        """
        query_tags = {t.lower().strip() for t in tags}
        results: List[StoreItem] = []

        for item in self.store:
            item_tags = {t.lower().strip() for t in item.tags}
            if match_all:
                if query_tags.issubset(item_tags):
                    results.append(item)
            else:
                if query_tags & item_tags:
                    results.append(item)

        return results

    def retrieve_history_by_similarity(
        self,
        query: Union[str, Dict[str, float]],
        k: int = 5
    ) -> List[Tuple[HistoryItem, float]]:
        """Retrieves top-k historical threads by embedding cosine similarity.
        
        Implements: prior = retrieve(history, embed(candidate), k=5)
        """
        if isinstance(query, str):
            query_vec = self.embedder.embed(query, self.idf)
        else:
            query_vec = query

        scored_items: List[Tuple[HistoryItem, float]] = []
        for item, item_vec in zip(self.history, self.history_embeddings):
            sim = self.embedder.cosine_similarity(query_vec, item_vec)
            scored_items.append((item, sim))

        # Sort descending by similarity score
        scored_items.sort(key=lambda x: x[1], reverse=True)
        return scored_items[:k]


# =====================================================================
# 4. UNIFIED MEMORY MANAGER (Enforcing Lab 4 Memory Split)
# =====================================================================

class MemoryManager:
    """Unified Memory Manager enforcing the strict separation of run state vs stored knowledge.
    
    Provides the exact Lab 4 pseudocode interfaces:
      state.draft = candidate
      hits = memory.retrieve(store, tags)
      prior = memory.retrieve(history, embed(candidate), k=5)
    """

    def __init__(
        self,
        session_state: Optional[SessionState] = None,
        long_term_store: Optional[LongTermMemoryStore] = None,
    ):
        self.state = session_state or SessionState(session_id="session_default")
        self.long_term = long_term_store or LongTermMemoryStore()

    def embed(self, text_or_candidate: Union[str, DraftReply, EmailThread, Dict[str, Any]]) -> Dict[str, float]:
        """Produces a lightweight local TF-IDF embedding for candidate text."""
        if isinstance(text_or_candidate, str):
            text = text_or_candidate
        elif isinstance(text_or_candidate, DraftReply):
            text = f"{text_or_candidate.subject} {text_or_candidate.body}"
        elif isinstance(text_or_candidate, EmailThread):
            text = f"{text_or_candidate.subject} {text_or_candidate.snippet} " + " ".join(m.body for m in text_or_candidate.messages)
        elif isinstance(text_or_candidate, dict):
            text = f"{text_or_candidate.get('subject', '')} {text_or_candidate.get('body', '')} {text_or_candidate.get('snippet', '')}"
        else:
            text = str(text_or_candidate)

        return self.long_term.embedder.embed(text, self.long_term.idf)

    def retrieve(
        self,
        target: str,
        tags: Optional[List[str]] = None,
        query: Optional[Union[str, Dict[str, float]]] = None,
        k: int = 5,
        match_all: bool = False
    ) -> Any:
        """Universal retrieval method for store (by tags) and history (by similarity).
        
        Syntactic compatibility with Chapter 3 pseudocode:
          hits = retrieve(store, tags)
          prior = retrieve(history, embed(candidate), k=5)
        """
        target_normalized = target.lower().strip()

        if "store" in target_normalized:
            # Long-term reference store retrieval by tags
            tag_list = tags or []
            return self.long_term.retrieve_store_by_tags(tag_list, match_all=match_all)

        elif "history" in target_normalized or "prior" in target_normalized:
            # Long-term historical archive retrieval by embedding similarity
            if query is None:
                raise ValueError("Query or candidate embedding vector is required for history retrieval.")
            return self.long_term.retrieve_history_by_similarity(query, k=k)

        else:
            raise ValueError(f"Unknown retrieval target '{target}'. Must be 'store' or 'history'.")
