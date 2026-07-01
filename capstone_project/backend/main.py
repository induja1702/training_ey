import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_PATH = ROOT_DIR / "backend"
if BACKEND_PATH.exists() and str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from src.api.upload_api import router as upload_router
from src.api.chat import router as chat_router
from src.observability.langsmith import tracing_context, _get_client, _get_project_name, is_enabled


class LangSmithRequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        with tracing_context(
            client=_get_client(),
            enabled=is_enabled(),
            project_name=_get_project_name(),
        ):
            return await call_next(request)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Contract Intelligence Chatbot",
    description="AI-powered contract analysis using Knowledge RAG and Agentic RAG pipelines.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    LangSmithRequestTracingMiddleware,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Streamlit dev origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/upload", tags=["Upload"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )