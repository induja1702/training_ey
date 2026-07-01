"""
Shared singleton for all ingestion + retrieval components.
Both upload_api and chat_api import from here so they share
the same in-memory FAISS index — uploads are instantly visible to chat.
"""
from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parents[1] / ".env", override=True)

logger = logging.getLogger(__name__)


class _UnavailableParser:
    def parse(self, pdf_path):
        raise RuntimeError("PDF parsing dependencies are unavailable.")


class _UnavailableChunker:
    def chunk(self, pages, doc_id, filename):
        raise RuntimeError("Text chunking dependencies are unavailable.")


class _UnavailableEmbedder:
    embedding_model = None


class _UnavailableVectorStore:
    def add_documents(self, documents):
        return None

    def delete_document(self, doc_id):
        return None


_parser = None
_chunker = None
_embedder = None
_vector_store = None


def get_pipeline():
    global _parser, _chunker, _embedder, _vector_store
    if _embedder is None:
        logger.info("Initialising shared ingestion pipeline...")
        try:
            from docs.parser import PDFParser
            from docs.chunking import DocumentChunker
            from docs.embedding import OpenAIEmbedder
            from docs.vector_store import FAISSVectorStore
        except Exception as exc:
            logger.warning("Pipeline dependencies unavailable; using stub components. %s", exc, exc_info=True)
            _parser = _UnavailableParser()
            _chunker = _UnavailableChunker()
            _embedder = _UnavailableEmbedder()
            _vector_store = _UnavailableVectorStore()
            logger.info("Pipeline ready with fallback components.")
            return _parser, _chunker, _vector_store

        _parser = PDFParser()
        _chunker = DocumentChunker()
        _embedder = OpenAIEmbedder()
        _vector_store = FAISSVectorStore(
            index_dir="faiss_index",
            embedding_model=_embedder.embedding_model,
        )
        logger.info("Pipeline ready.")
    return _parser, _chunker, _vector_store


def get_vector_store():
    _, _, vs = get_pipeline()
    return vs


def get_embedder():
    get_pipeline()
    return _embedder
