"""
retriever.py
------------
Hybrid BM25 + dense retriever and cross-encoder reranker.

Updated to work with PineconeVectorStoreManager (was FAISSVectorStore).

The only meaningful change from the FAISS version:
  - BM25 document source:  vector_store.get_all_documents()
    instead of the internal  vector_store.vector_store.docstore._dict

  - Optional doc_id scoping added to build_hybrid_retriever() so BM25
    and dense retrieval can both be filtered to a single document.

Dependencies (add to requirements.txt):
    rank_bm25>=0.2.2
    sentence-transformers>=2.7.0
    langchain-pinecone>=0.2.0
    pinecone>=5.0.0
"""

from __future__ import annotations

import logging
from typing import Optional

from langchain_community.retrievers import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

# Lazy-loaded singleton — model loads on first call (~200 MB, once per process)
_cross_encoder: Optional[CrossEncoder] = None


def _get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        logger.info("Loading cross-encoder model (first call only)...")
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        logger.info("Cross-encoder ready.")
    return _cross_encoder


def build_hybrid_retriever(
    vector_store,                    # PineconeVectorStoreManager instance
    doc_id: Optional[str] = None,   # Scope both retrievers to one document
    k: int = 20,
    bm25_weight: float = 0.4,
    dense_weight: float = 0.6,
) -> EnsembleRetriever:
    """
    Build a BM25 + dense EnsembleRetriever backed by Pinecone.

    BM25 handles exact-match terms ("Effective Date", "Force Majeure").
    Dense handles semantic similarity.
    Weights drive Reciprocal Rank Fusion inside EnsembleRetriever.

    Change from FAISS version
    ─────────────────────────
    FAISS:   all_docs = list(vector_store.vector_store.docstore._dict.values())
    Pinecone: all_docs = vector_store.get_all_documents(doc_id=doc_id)

    Pinecone's list + fetch APIs transfer only IDs then metadata — no
    embedding vectors are downloaded — so this is relatively lightweight.

    NOTE: rebuild this retriever after each upload batch; BM25 is a
    snapshot of the index at construction time.
    """
    all_docs: list[Document] = vector_store.get_all_documents(doc_id=doc_id)

    if not all_docs:
        raise RuntimeError(
            "Pinecone index is empty — upload at least one document "
            "before building the retriever."
        )

    logger.info("Building BM25 from %d chunks.", len(all_docs))
    bm25 = BM25Retriever.from_documents(all_docs, k=k)

    dense_filter = {"doc_id": {"$eq": doc_id}} if doc_id else None
    dense = vector_store.vector_store.as_retriever(
        search_kwargs={
            "k":         k,
            "filter":    dense_filter,
            "namespace": vector_store.namespace,
        }
    )

    logger.info(
        "EnsembleRetriever ready  BM25=%.1f  dense=%.1f  k=%d  doc_id=%s",
        bm25_weight, dense_weight, k, doc_id or "all",
    )

    return EnsembleRetriever(
        retrievers=[bm25, dense],
        weights=[bm25_weight, dense_weight],
    )


def rerank(
    query: str,
    docs: list[Document],
    top_n: int = 5,
) -> list[Document]:
    """
    Re-rank candidates with a cross-encoder and return top_n.

    The cross-encoder scores (query, passage) pairs jointly, catching
    relevance signals cosine similarity misses (negation, specificity).

    No changes from the FAISS version — this function is vector-store agnostic.
    """
    if not docs:
        return []

    cross_encoder = _get_cross_encoder()
    pairs  = [(query, doc.page_content) for doc in docs]
    scores = cross_encoder.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    top    = [doc for doc, _ in ranked[:top_n]]

    logger.info(
        "Reranked %d → %d  (top score: %.4f  bottom kept: %.4f)",
        len(docs), len(top),
        ranked[0][1]           if ranked             else 0.0,
        ranked[top_n - 1][1]   if len(ranked) >= top_n else 0.0,
    )

    return top