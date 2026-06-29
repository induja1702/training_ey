"""
embedding.py
------------

Responsibility:
Create and manage the OpenAI embedding model.

Pipeline:

Chunk Documents
        │
        ▼
OpenAI Embeddings
        │
        ▼
FAISS Vector Store
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

load_dotenv()


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

@dataclass
class EmbeddingConfig:
    """
    Configuration for OpenAI Embeddings.
    """

    model: str = "text-embedding-3-small"

    # Optional
    dimensions: int | None = None


# ---------------------------------------------------------
# OpenAI Embedder
# ---------------------------------------------------------

class OpenAIEmbedder:
    """
    Wrapper around LangChain OpenAIEmbeddings.

    This object is reused by FAISS for:
        - document embeddings
        - query embeddings

    Using one embedding model ensures vectors
    are always in the same embedding space.
    """

    def __init__(
        self,
        config: EmbeddingConfig | None = None,
    ):

        self.config = config or EmbeddingConfig()

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables."
            )

        kwargs = {
            "model": self.config.model,
            "api_key": api_key,
        }

        # dimensions only supported for text-embedding-3 models
        if self.config.dimensions:
            kwargs["dimensions"] = self.config.dimensions

        logger.info(
            "Initializing embedding model '%s'...",
            self.config.model,
        )

        self.embeddings = OpenAIEmbeddings(**kwargs)

        logger.info("Embedding model initialized successfully.")

    @property
    def embedding_model(self) -> OpenAIEmbeddings:
        """
        Return the LangChain embedding model.

        This object should be passed directly to FAISS.
        """
        return self.embeddings

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a user query.

        Used during similarity search.
        """

        return self.embeddings.embed_query(query)