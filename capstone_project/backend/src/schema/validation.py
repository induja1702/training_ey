from typing import List
from pydantic import BaseModel


class UploadedFile(BaseModel):
    file_id: str
    original_name: str
    # blob_url: str
    size_bytes: int


class UploadResponse(BaseModel):
    session_id: str
    message: str
    uploaded_count: int
    failed_count: int
    files: List[UploadedFile]
    errors: List[dict]


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    reset_session: bool = False


class ChatResponse(BaseModel):
    session_id: str
    query: str
    answer: str
    sources: list[str]
    intent: str
    intent_reason: str


class ChatHistoryItem(BaseModel):
    role: str
    text: str
    timestamp: str


class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_active: str
    turn_count: int


class SessionHistoryResponse(BaseModel):
    session_id: str
    history: List[ChatHistoryItem]


class DocumentStatus(BaseModel):
    doc_id: str
    filename: str
    blob_name: str
    blob_url: str
    size_bytes: int
    indexed: bool
    deleted: bool
    uploaded_at: str


class DocumentListResponse(BaseModel):
    count: int
    documents: List[DocumentStatus]