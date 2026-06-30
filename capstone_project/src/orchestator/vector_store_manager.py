"""
vector_store_manager.py

Both upload_api.py and chat.py currently share ONE global FAISSVectorStore
pointed at "faiss_index/". That means every chat session sees every
document anyone has ever uploaded — there's no isolation per chat.

This manager gives each session_id its own FAISS index directory
("faiss_index/<session_id>/") and caches the FAISSVectorStore instances in
memory per-process so repeated calls for the same session reuse the loaded
index instead of reloading it from disk every request.
"""

import logging
import threading

from docs.embedding import OpenAIEmbedder
from docs.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)

BASE_INDEX_DIR = "faiss_index"

_lock = threading.Lock()
_store_cache: dict[str, FAISSVectorStore] = {}
_embedder = OpenAIEmbedder()


def get_vector_store(session_id: str) -> FAISSVectorStore:
    """Returns the FAISSVectorStore scoped to this session, creating it on first use."""
    if session_id in _store_cache:
        return _store_cache[session_id]

    with _lock:
        if session_id in _store_cache:  # re-check after acquiring lock
            return _store_cache[session_id]

        store = FAISSVectorStore(
            index_dir=f"{BASE_INDEX_DIR}/{session_id}",
            embedding_model=_embedder.embedding_model,
        )
        _store_cache[session_id] = store
        logger.info("Initialized vector store for session %s", session_id)
        return store


def drop_vector_store(session_id: str) -> None:
    """Evict a session's store from the in-memory cache (e.g. after session deletion)."""
    with _lock:
        _store_cache.pop(session_id, None)