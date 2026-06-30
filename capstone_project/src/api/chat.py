import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
from openai import OpenAI
from src.agents.agentic_rag import AgenticRAG
from src.agents.intent_detection import IntentDetector, Workflow
from src.agents.knowledge_rag import KnowledgeRAG
from src.orchestator.session_store import session_store              # adjust import path to match your project
from src.orchestator.vector_store_manager import get_vector_store     # adjust import path to match your project
from src.schema.validation import (
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    DocumentListResponse,
    DocumentStatus,
    SessionHistoryResponse,
    SessionInfo,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Load environment variables and OpenAI key
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is required for the chat API.")

client = OpenAI(api_key=api_key)
intent_detector = IntentDetector()

# NOTE: knowledge_rag / agentic_rag are now constructed per-request with the
# session's own vector store (see chat_documents below) instead of one
# shared global instance — this is what scopes retrieval to this chat's docs.


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
    summary="Submit a chat query and route to the appropriate RAG path, scoped to this session's documents.",
)
async def chat_documents(request: ChatRequest) -> ChatResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query text cannot be empty.",
        )

    if not request.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required. Upload a document via /upload/ first to obtain one.",
        )

    session_id = session_store.make_session(request.session_id, request.reset_session)

    if not session_store.has_documents(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents have been uploaded to this chat session yet. Upload a document first.",
        )

    history_context = session_store.history_context(session_id)
    session_store.append_history(session_id, "user", query)

    # Per-session vector store + per-session RAG agents — this is what
    # keeps this chat's retrieval scoped to only the docs uploaded here.
    vector_store = get_vector_store(session_id)
    knowledge_rag = KnowledgeRAG(client=client, vector_store=vector_store, top_k=5)
    agentic_rag = AgenticRAG(client=client, vector_store=vector_store, top_k=5)

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

    session_store.append_history(session_id, "assistant", answer)
    return ChatResponse(
        session_id=session_id,
        query=query,
        answer=answer,
        sources=sources,
        intent=intent.workflow.value,
        intent_reason=intent.reason,
    )


@router.get(
    "/sessions",
    response_model=list[SessionInfo],
    summary="List active chat sessions.",
)
async def list_sessions():
    return [SessionInfo(**row) for row in session_store.list_sessions()]


@router.get(
    "/history/{session_id}",
    response_model=SessionHistoryResponse,
    summary="Retrieve chat history for a session.",
)
async def get_session_history(session_id: str):
    if not session_store.session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return SessionHistoryResponse(
        session_id=session_id,
        history=[ChatHistoryItem(**item) for item in session_store.get_history(session_id)],
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session, its history, and its document records.",
)
async def delete_session(session_id: str):
    if not session_store.session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    session_store.delete_session(session_id)  # CASCADE removes history + documents rows too


@router.get(
    "/documents/{session_id}",
    response_model=DocumentListResponse,
    summary="List documents uploaded within this chat session.",
)
async def get_document_list(session_id: str):
    if not session_store.session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    docs = session_store.list_documents(session_id)
    return DocumentListResponse(
        count=len(docs),
        documents=[
            DocumentStatus(
                file_id=d["file_id"],
                filename=d["original_name"],
                status=d["status"],
            )
            for d in docs
        ],
    )