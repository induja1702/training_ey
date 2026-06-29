import logging
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
from openai import OpenAI
from src.agents.intent_detection import detect_intent, IntentAgent
from pydantic import BaseModel

from docs.embedding import OpenAIEmbedder
from docs.vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)
router = APIRouter()

# Load environment variables and OpenAI key
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is required for the chat API.")

client = OpenAI(api_key=api_key)

# Initialize retrieval components
embedder = OpenAIEmbedder()
vector_store = FAISSVectorStore(
    index_dir="faiss_index",
    embedding_model=embedder.embedding_model,
)
top_k: int = 5




def build_prompt(question: str, sources: list[dict]) -> str:
    source_text = "\n\n".join(
        f"Source: {item['source']}\n{item['content']}"
        for item in sources
    )

    return (
        "You are a helpful assistant. Use the following extracted document passages to answer the user's question. "
        "If the answer is not contained in the passages, say that you cannot answer based on the provided documents.\n\n"
        f"{source_text}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )


def create_chat_answer(question: str, document_texts: list[dict]) -> str:
    prompt = build_prompt(question, document_texts)

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {"role": "system", "content": "You are a helpful document assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_output_tokens=400,
    )

    output_text = ""
    if getattr(response, "output_text", None):
        output_text = response.output_text
    elif getattr(response, "output", None):
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for content_item in getattr(item, "content", []) or []:
                    if getattr(content_item, "type", None) == "output_text":
                        output_text = getattr(content_item, "text", "")
                        break
                if output_text:
                    break

    return output_text.strip()


@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the uploaded documents",
)
async def chat_documents(request: ChatRequest) -> ChatResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query text cannot be empty.",
        )

    if vector_store.vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No indexed documents are available for search.",
        )

    # detect intent first
    intent = detect_intent(query)
    logger.info("Intent detected: %s (%.2f) - %s", intent.get("intent"), intent.get("confidence"), intent.get("reason"))

    if intent.get("intent") == "simple":
        docs = vector_store.similarity_search(query=query, k=top_k)
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant document chunks found for the query.",
            )

        sources = []
        source_payload = []
        for doc in docs:
            metadata = doc.metadata or {}
            source_name = metadata.get("filename") or metadata.get("source") or "document"
            page_number = metadata.get("page")
            if page_number is not None:
                source_name = f"{source_name} (page {page_number})"

            text = doc.page_content.strip()
            sources.append(source_name)
            source_payload.append({"source": source_name, "content": text})

        answer = create_chat_answer(query, source_payload)
        return ChatResponse(query=query, answer=answer, sources=sources)

    # complex intent -> use IntentAgent to synthesize
    docs = vector_store.similarity_search(query=query, k=top_k * 4)
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant document chunks found for the query.",
        )

    sources = []
    source_payload = []
    for doc in docs:
        metadata = doc.metadata or {}
        source_name = metadata.get("filename") or metadata.get("source") or "document"
        page_number = metadata.get("page")
        if page_number is not None:
            source_name = f"{source_name} (page {page_number})"

        text = doc.page_content.strip()
        sources.append(source_name)
        source_payload.append({"source": source_name, "content": text})

    agent = IntentAgent()
    result = agent.run(query, source_payload)
    answer = result.get("answer", "")
    return ChatResponse(query=query, answer=answer, sources=sources)
