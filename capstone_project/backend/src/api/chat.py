import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
from openai import OpenAI

from src.agents.agentic_rag import AgenticRAG
from src.observability.langsmith import traceable_operation
from src.agents.intent_detection import IntentDetector, Workflow
from src.agents.knowledge_rag import KnowledgeRAG
from src.orchestator.session_store_postgres import SessionStore
from src.retrieval.doc_registry import list_documents
from src.schema.validation import (
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    DocumentListResponse,
    DocumentStatus,
    SessionHistoryResponse,
)
from docs.pipeline import get_vector_store

load_dotenv(dotenv_path=Path(__file__).parents[2] / ".env", override=True)

logger = logging.getLogger(__name__)
router = APIRouter()

session_man = SessionStore()
MAX_HISTORY_ITEMS = 20

# ---------------------------------------------------------------------------
# Lazy-initialised singletons (created on first request, not at import time)
# ---------------------------------------------------------------------------

_openai_client: OpenAI | None = None
_intent_detector: IntentDetector | None = None
_knowledge_rag: KnowledgeRAG | None = None
_agentic_rag: AgenticRAG | None = None


def _get_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _get_agents() -> tuple[IntentDetector, KnowledgeRAG, AgenticRAG]:
    global _intent_detector, _knowledge_rag, _agentic_rag
    client = _get_client()
    vector_store = get_vector_store()
    if _intent_detector is None:
        _intent_detector = IntentDetector()
    if _knowledge_rag is None:
        _knowledge_rag = KnowledgeRAG(client=client, vector_store=vector_store, top_k=5)
    if _agentic_rag is None:
        _agentic_rag = AgenticRAG(client=client, vector_store=vector_store, top_k=5)
    return _intent_detector, _knowledge_rag, _agentic_rag

# ---------------------------------------------------------------------------
# Source extraction
# ---------------------------------------------------------------------------

def _build_sources(docs: list) -> tuple[list[str], list[dict]]:
    sources: list[str] = []
    source_payload: list[dict] = []
    for item in docs:
        if isinstance(item, dict):
            content = item.get("content") or ""
            source_name = item.get("source") or "document"
            sources.append(source_name)
            source_payload.append({"source": source_name, "content": content})
            continue

        meta = getattr(item, "metadata", None) or {}
        name = meta.get("filename") or meta.get("source") or "document"
        page = meta.get("page")
        if page is not None:
            name = f"{name} (page {page})"
        sources.append(name)
        source_payload.append({"source": name, "content": getattr(item, "page_content", "").strip()})
    return sources, source_payload


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@traceable_operation(
    name="Chat request",
    tags=["api", "chat"],
    metadata={"endpoint": "/chat/"},
)
@router.post(
    "/",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a chat query — auto-routed to KnowledgeRAG or AgenticRAG.",
)
async def chat_documents(request: ChatRequest) -> ChatResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query text cannot be empty.",
        )

    session_id = session_man.make_session(request.session_id, request.reset_session)
    history_context = session_man.history_context(session_id)
    session_man.append_history(session_id, "user", query)

    vector_store = get_vector_store()
    if getattr(vector_store, "vector_store", None) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No indexed documents are available. Upload a PDF first via POST /upload/.",
        )

    intent_detector, knowledge_rag, agentic_rag = _get_agents()

    start = time.perf_counter()
    intent = intent_detector.detect(query)
    logger.info(
        "Intent detected: %s (%.2f) — %s",
        intent.workflow.value, intent.confidence, intent.reason,
    )

    if intent.workflow == Workflow.KNOWLEDGE_RAG:
        retrieval_result = knowledge_rag.retrieve(query)
        if isinstance(retrieval_result, tuple):
            docs, _ = retrieval_result
        else:
            docs = retrieval_result

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

    elapsed = time.perf_counter() - start
    logger.info(
        "Query answered in %.2fs. intent=%s sources=%d",
        elapsed, intent.workflow.value, len(sources),
    )

    session_man.append_history(session_id, "assistant", answer)
    return ChatResponse(
        session_id=session_id,
        query=query,
        answer=answer,
        sources=sources,
        intent=intent.workflow.value,
        intent_reason=intent.reason,
    )


@traceable_operation(
    name="Chat session history request",
    tags=["api", "chat", "history"],
    metadata={"endpoint": "/chat/history/{session_id}"},
)
@router.get(
    "/history/{session_id}",
    response_model=SessionHistoryResponse,
    summary="Retrieve chat history for a session.",
)
async def get_session_history(session_id: str) -> SessionHistoryResponse:
    session = session_man.get_session_info(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return SessionHistoryResponse(
        session_id=session_id,
        history=[ChatHistoryItem(**item) for item in session["history"]],
    )


@traceable_operation(
    name="Document list request",
    tags=["api", "chat", "documents"],
    metadata={"endpoint": "/chat/documents"},
)
@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all indexed documents.",
)
async def get_document_list() -> DocumentListResponse:
    docs = list_documents()
    return DocumentListResponse(
        count=len(docs),
        documents=[DocumentStatus(**doc) for doc in docs],
    )
