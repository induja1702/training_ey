import logging

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
    """
    Question -> Retrieve -> Response Generation -> Final Answer

    The simple, single-hop branch: one retrieval pass, one generation pass,
    no decomposition, no task routing, no validation step. Matches the
    interface chat.py already expects: retrieve(query) -> docs,
    answer(query, source_payload, history_context) -> str.
    """

    def __init__(self, client: OpenAI, vector_store: FAISSVectorStore, top_k: int = 5, model: str = "gpt-4o"):
        self.client = client
        self.vector_store = vector_store
        self.top_k = top_k
        self.model = model

    # -------------------------------------------------------------
    # Retrieve
    # -------------------------------------------------------------
    def retrieve(self, query: str) -> list:
        """Single retrieval pass against the shared vector store."""
        docs = self.vector_store.similarity_search(query=query, k=self.top_k)
        if not docs:
            logger.info("KnowledgeRAG: no documents retrieved for query: %s", query)
        return docs

    # -------------------------------------------------------------
    # Response Generation
    # -------------------------------------------------------------
    @staticmethod
    def _build_context(source_payload: list[dict]) -> str:
        if not source_payload:
            return "No relevant documents were retrieved."
        return "\n\n".join(
            f"Source: {item['source']}\n{item['content']}" for item in source_payload
        )

    def answer(self, query: str, source_payload: list[dict], history: str | None = None) -> str:
        """
        Generate the final answer directly from retrieved context.
        source_payload: list of {"source": ..., "content": ...} dicts,
        as already built by _build_sources() in chat.py.
        """
        context = self._build_context(source_payload)
        history_section = f"Previous conversation:\n{history}\n\n" if history else ""

        prompt = (
            "You are a precise contract knowledge assistant. Answer the user's question using ONLY the "
            "provided context. Reference the relevant source name(s) in your answer. If the context does "
            "not contain the answer, say so explicitly instead of guessing.\n\n"
            f"{history_section}"
            f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
        )
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": "You are a precise, grounded contract knowledge assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_output_tokens=500,
        )
        answer_text = _extract_response_text(response).strip()
        if not answer_text:
            logger.warning("KnowledgeRAG: empty response from model for query: %s", query)
            return "I couldn't generate an answer from the retrieved documents."
        return answer_text

    # -------------------------------------------------------------
    # Convenience: full branch in one call (retrieve + answer)
    # -------------------------------------------------------------
    def run(self, query: str, history: str | None = None) -> dict:
        docs = self.retrieve(query)
        source_payload = []
        for doc in docs:
            metadata = doc.metadata or {}
            source_name = metadata.get("filename") or metadata.get("source") or "document"
            page_number = metadata.get("page")
            if page_number is not None:
                source_name = f"{source_name} (page {page_number})"
            source_payload.append({"source": source_name, "content": doc.page_content.strip()})

        answer_text = self.answer(query, source_payload, history)
        return {"answer": answer_text, "docs": docs, "sources": source_payload}