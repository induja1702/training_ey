"""
chunking.py
-----------

Responsibility:
Split parsed PDF pages into overlapping chunks and
attach metadata required for retrieval.

Pipeline:

List[Document]
        │
        ▼
RecursiveCharacterTextSplitter
        │
        ▼
Chunk Documents + Metadata
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

@dataclass
class ChunkConfig:
    """
    Configuration for RecursiveCharacterTextSplitter.
    """

    chunk_size: int = 1000
    chunk_overlap: int = 200

    separators: list[str] = field(default_factory=lambda: [
        "\n\n",
        "\n",
        ". ",
        ", ",
        " ",
        ""
    ])


# ---------------------------------------------------------
# Document Chunker
# ---------------------------------------------------------

class DocumentChunker:

    def __init__(self, config: ChunkConfig | None = None):

        self.config = config or ChunkConfig()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk(
        self,
        pages: list[Document],
        doc_id: str,
        filename: str,
    ) -> list[Document]:
        """
        Split PDF pages into chunks.

        Parameters
        ----------
        pages : List[Document]

        doc_id : UUID generated during upload

        filename : Original filename

        Returns
        -------
        List[Document]
        """

        if not pages:
            raise ValueError("No pages found to chunk.")

        logger.info(
            "Chunking '%s' (%d pages)...",
            filename,
            len(pages),
        )

        all_chunks: list[Document] = []

        total_chunks = 0

        for page_doc in pages:

            page_number = page_doc.metadata.get("page", 0) + 1

            page_chunks = self.text_splitter.split_documents([page_doc])

            for chunk_index, chunk in enumerate(page_chunks):

                chunk.metadata.update(
                    {
                        # Document Information
                        "doc_id": doc_id,
                        "filename": filename,

                        # PDF Information
                        "page": page_number,

                        # Chunk Information
                        "chunk_index": chunk_index,
                        "chunk_size": len(chunk.page_content),

                        # Useful for highlighting later
                        "char_start": (
                            chunk_index
                            * (
                                self.config.chunk_size
                                - self.config.chunk_overlap
                            )
                        ),
                    }
                )

                all_chunks.append(chunk)

                total_chunks += 1

        logger.info(
            "Generated %d chunks from '%s'.",
            total_chunks,
            filename,
        )

        return all_chunks