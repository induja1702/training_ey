import logging
from openai import OpenAI
from docs.vector_store import FAISSVectorStore
from src.agents.knowledge_rag import KnowledgeRAG

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


class AgenticRAG:

    def __init__(self, client: OpenAI, vector_store: FAISSVectorStore, top_k: int = 5, model: str = "gpt-4o"):
        self.client = client
        self.vector_store = vector_store
        self.top_k = top_k
        self.model = model
        self.knowledge_rag = KnowledgeRAG(client=client, vector_store=vector_store, model=model, top_k=top_k)

    def analyze_query(self, question: str) -> list[str]:
        prompt = (
            "You are a query analysis agent. Decompose the following user question into up to three retrieval-guided subquestions. "
            "Return each subquestion on a new line without numbering or extra commentary.\n\n"
            f"Question: {question}\n"
            "Subquestions:"
        )
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": "Decompose a user query into subquestions for retrieval."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_output_tokens=200,
        )
        output_text = _extract_response_text(response)
        lines = [line.strip("- ").strip() for line in output_text.splitlines() if line.strip()]
        return lines or [question]

    def run(self, question: str, history: str | None = None) -> dict:
        subquestions = self.analyze_query(question)
        retrieved = []
        for sub in subquestions:
            docs = self.vector_store.similarity_search(query=sub, k=self.top_k)
            retrieved.append({"subquestion": sub, "docs": docs})

        sources = []
        for item in retrieved:
            for doc in item["docs"]:
                metadata = doc.metadata or {}
                source_name = metadata.get("filename") or metadata.get("source") or "document"
                page_number = metadata.get("page")
                if page_number is not None:
                    source_name = f"{source_name} (page {page_number})"
                sources.append({
                    "subquestion": item["subquestion"],
                    "source": source_name,
                    "content": doc.page_content.strip(),
                })

        context = "\n\n".join(
            f"Subquestion: {item['subquestion']}\nSource: {item['source']}\n{item['content']}"
            for item in sources
        )
        history_section = f"Previous conversation:\n{history}\n\n" if history else ""
        synth_prompt = (
            "You are an expert contract reasoning assistant. Use the provided passages to answer the user's original question. "
            "Explicitly reference the source names and verify the answer against the evidence.\n\n"
            f"{history_section}"
            f"{context}\n\nQuestion: {question}\nAnswer:"
        )
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": "You are an expert assistant that synthesizes multiple documents and validates citations."},
                {"role": "user", "content": synth_prompt},
            ],
            temperature=0.2,
            max_output_tokens=600,
        )
        answer = _extract_response_text(response).strip()
        return {"answer": answer, "retrieved": retrieved}
