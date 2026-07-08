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
    chunks: List[dict] = []
    intent: str
    intent_reason: str
    intent_confidence: float = 0.0
    llm_latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


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


class RateLimitError(BaseModel):
    """Response body returned with HTTP 429 Too Many Requests.

    Matches the JSON shape produced by :class:`RateLimiterMiddleware`:

    .. code-block:: json

        {
            "detail": "Rate limit exceeded. Try again in 42 second(s).",
            "retry_after": 42
        }
    """

    detail: str
    retry_after: int