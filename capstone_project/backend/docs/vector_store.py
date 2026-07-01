"""
vector_store.py
---------------

Responsibility:
Manage the FAISS vector database.

Pipeline

Chunk Documents
        │
        ▼
OpenAI Embeddings
        │
        ▼
FAISS
        │
        ▼
Similarity Search
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)


class FAISSVectorStore:

    INDEX_NAME = "index"

    def __init__(
        self,
        index_dir: str,
        embedding_model: Embeddings,
    ):

        self.index_dir = Path(index_dir)

        self.index_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.embedding_model = embedding_model

        self.vector_store = self._load()

    # --------------------------------------------------
    # Private Methods
    # --------------------------------------------------

    def _load(self) -> Optional[FAISS]:

        index_file = self.index_dir / f"{self.INDEX_NAME}.faiss"

        if not index_file.exists():

            logger.info(
                "No FAISS index found. A new index will be created."
            )

            return None

        logger.info("Loading existing FAISS index...")

        return FAISS.load_local(
            folder_path=str(self.index_dir),
            embeddings=self.embedding_model,
            index_name=self.INDEX_NAME,
            allow_dangerous_deserialization=True,
        )

    def _save(self):

        if self.vector_store is None:
            return

        self.vector_store.save_local(
            folder_path=str(self.index_dir),
            index_name=self.INDEX_NAME,
        )

        logger.info(
            "FAISS index saved successfully."
        )

    # --------------------------------------------------
    # Public Methods
    # --------------------------------------------------

    def add_documents(
        self,
        documents: list[Document],
    ):

        if not documents:

            logger.warning(
                "No documents received for indexing."
            )

            return

        if self.vector_store is None:

            logger.info(
                "Creating new FAISS index..."
            )

            self.vector_store = FAISS.from_documents(
                documents=documents,
                embedding=self.embedding_model,
            )

        else:

            logger.info(
                "Adding %d new chunks to FAISS.",
                len(documents),
            )

            self.vector_store.add_documents(
                documents=documents,
            )

        self._save()

    # --------------------------------------------------

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        doc_id: Optional[str] = None,
    ) -> list[Document]:

        if self.vector_store is None:

            logger.warning(
                "FAISS index is empty."
            )

            return []

        search_filter = (
            {"doc_id": doc_id}
            if doc_id
            else None
        )

        results = self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=search_filter,
        )

        return results

    # --------------------------------------------------

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        doc_id: Optional[str] = None,
    ):

        if self.vector_store is None:

            return []

        search_filter = (
            {"doc_id": doc_id}
            if doc_id
            else None
        )

        return self.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=search_filter,
        )

    # --------------------------------------------------

    def document_count(self):

        if self.vector_store is None:
            return 0

        return len(self.vector_store.docstore._dict)

    # --------------------------------------------------

    def get_all_doc_ids(self):

        if self.vector_store is None:
            return []

        return sorted({

            document.metadata.get("doc_id")

            for document in self.vector_store.docstore._dict.values()

            if document.metadata.get("doc_id")

        })

    # --------------------------------------------------

    def delete_document(
        self,
        doc_id: str,
    ):

        if self.vector_store is None:
            return

        logger.info(
            "Deleting document %s from FAISS.",
            doc_id,
        )

        remaining_documents = [

            doc

            for doc in self.vector_store.docstore._dict.values()

            if doc.metadata.get("doc_id") != doc_id

        ]

        if not remaining_documents:

            self.vector_store = None

            for file in self.index_dir.glob("index.*"):
                file.unlink(missing_ok=True)

            logger.info("FAISS index cleared.")

            return

        self.vector_store = FAISS.from_documents(
            documents=remaining_documents,
            embedding=self.embedding_model,
        )

        self._save()

        logger.info(
            "Document deleted successfully."
        )