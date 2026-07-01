"""
parser.py
---------

Responsibility:
Load a PDF from disk and convert it into LangChain Documents.

Pipeline:
PDF File
    │
    ▼
PyPDFLoader
    │
    ▼
List[Document]
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class PDFParser:
    """
    Loads PDF documents using LangChain's PyPDFLoader.

    Output:
        List[Document]

    Each Document contains:
        - page_content
        - metadata
            page
            source
    """

    def parse(self, pdf_path: str | Path) -> list[Document]:
        """
        Parse a PDF into LangChain Documents.

        Parameters
        ----------
        pdf_path : str | Path

        Returns
        -------
        List[Document]
        """

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Loading PDF: {pdf_path.name}")

        loader = PyPDFLoader(str(pdf_path))

        pages = loader.load()

        logger.info(
            "Parsed '%s' into %d page(s).",
            pdf_path.name,
            len(pages)
        )

        return pages