import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
from openai import OpenAI
from src.agents.agentic_rag import AgenticRAG
from src.agents.intent_detection import IntentDetector, Workflow
from src.agents.knowledge_rag import KnowledgeRAG
from src.retrival.doc_registry import list_documents
from src.schema.validation import (
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    DocumentListResponse,
    DocumentStatus,
    SessionHistoryResponse,
    SessionInfo,
)

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
intent_detector = IntentDetector()
knowledge_rag = KnowledgeRAG(client=client, vector_store=vector_store, top_k=5)
agentic_rag = AgenticRAG(client=client, vector_store=vector_store, top_k=5)

SESSION_STORE: dict[str, dict[str, Any]] = {}
MAX_HISTORY_ITEMS = 20


def _make_session(session_id: str | None = None, reset: bool = False) -> str:
    if reset or not session_id or session_id not in SESSION_STORE:
        session_id = str(uuid.uuid4())
        SESSION_STORE[session_id] = {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_active": datetime.utcnow().isoformat() + "Z",
            "history": [],
            "turn_count": 0,
        }
    return session_id


def _append_history(session_id: str, role: str, text: str) -> None:
    session = SESSION_STORE[session_id]
    session["history"].append(
        {
            "role": role,
            "text": text,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    )
    session["history"] = session["history"][-MAX_HISTORY_ITEMS:]
    session["last_active"] = datetime.utcnow().isoformat() + "Z"
    session["turn_count"] = len(session["history"]) // 2


def _history_context(session_id: str) -> str | None:
    history = SESSION_STORE.get(session_id, {}).get("history", [])
    if not history:
        return None
    return "\n".join(
        f"{item['role'].capitalize()}: {item['text']}" for item in history
    )


def _extract_response_text(response: Any) -> str:
    if getattr(response, "output_text", None):
        return response.output_text
    if getattr(response, "output", None):
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for content_item in getattr(item, "content", []) or []:
                    if getattr(content_item, "type", None) == "output_text":
                        return getattr(content_item, "text", "")
    return ""


def _build_sources(docs: list) -> tuple[list[str], list[dict]]:
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
    return sources, source_payload


@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a chat query and route to the appropriate RAG path.",
)
async def chat_documents(request: ChatRequest) -> ChatResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query text cannot be empty.",
        )

    session_id = _make_session(request.session_id, request.reset_session)
    history_context = _history_context(session_id)
    _append_history(session_id, "user", query)

    if vector_store.vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No indexed documents are available for search.",
        )

    start_time = time.perf_counter()
    intent = intent_detector.detect(query)
    logger.info(
        "Intent detected: %s (%.2f) - %s",
        intent.workflow.value, intent.confidence, intent.reason
    )

    if intent.workflow == Workflow.KNOWLEDGE_RAG:
        docs = knowledge_rag.retrieve(query)
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant document chunks found for the query.",
            )
        sources, source_payload = _build_sources(docs)
        answer = knowledge_rag.answer(query, source_payload, history_context)
    else:
        agent_result = agentic_rag.run(query, history_context)
        answer = agent_result.get("answer", "")
        docs = []
        for item in agent_result.get("retrieved", []):
            docs.extend(item.get("docs", []))
        sources, _ = _build_sources(docs)

    elapsed = time.perf_counter() - start_time
    logger.info(
        "Query processed in %.2f seconds. Intent=%s. Retrieved %d docs.",
        elapsed, intent.workflow.value, len(sources),
    )

    _append_history(session_id, "assistant", answer)
    return ChatResponse(
        session_id=session_id,
        query=query,
        answer=answer,
        sources=sources,
        intent=intent.workflow.value,
        intent_reason=intent.reason,
    )


@router.get(
    "/history/{session_id}",
    response_model=SessionHistoryResponse,
    summary="Retrieve chat history for a session.",
)
async def get_session_history(session_id: str):
    session = SESSION_STORE.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return SessionHistoryResponse(
        session_id=session_id,
        history=[ChatHistoryItem(**item) for item in session["history"]],
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List documents and indexing status.",
)
async def get_document_list():
    docs = list_documents()
    return DocumentListResponse(
        count=len(docs),
        documents=[DocumentStatus(**doc) for doc in docs],
    )
