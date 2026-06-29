from typing import List
from pydantic import BaseModel


class UploadedFile(BaseModel):
    file_id: str
    original_name: str
    blob_url: str
    size_bytes: int


class UploadResponse(BaseModel):
    message: str
    uploaded_count: int
    failed_count: int
    files: List[UploadedFile]
    errors: List[dict]

class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: list[str]