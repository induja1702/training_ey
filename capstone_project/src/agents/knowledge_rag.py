import logging
from typing import List

from openai import OpenAI
from docs.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


def _extract_response_text(response) -> str:
    if getattr(response, "output_text", None):
        return response.output_text
    if getattr(response, "output", None):
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for content_item in getattr(item, "content", []) or []:
                    if getattr(content_item, "type", None) == "output_text":
                        return getattr(content_item, "text", "")
    return ""


class KnowledgeRAG:

    def __init__(
        self,
        client: OpenAI,
        vector_store: FAISSVectorStore,
        model: str = "gpt-4o",
        top_k: int = 5,
    ):
        self.client = client
        self.vector_store = vector_store
        self.model = model
        self.top_k = top_k

    def retrieve(self, query: str):
        return self.vector_store.similarity_search(query=query, k=self.top_k)

    def build_prompt(self, question: str, sources: List[dict], history: str | None = None) -> str:
        source_text = "\n\n".join(
            f"Source: {item['source']}\n{item['content']}"
            for item in sources
        )
        history_section = f"Previous conversation:\n{history}\n\n" if history else ""
        return (
            "You are a helpful contract intelligence assistant. Answer using only the provided document passages. "
            "Cite each passage by source. If you cannot answer from the passages, say so clearly.\n\n"
            f"{history_section}"
            f"{source_text}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

    def answer(self, question: str, sources: List[dict], history: str | None = None) -> str:
        prompt = self.build_prompt(question, sources, history)
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": "You are a helpful document assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_output_tokens=450,
        )
        return _extract_response_text(response).strip()
