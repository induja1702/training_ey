import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_PATH = ROOT_DIR / "backend"
if BACKEND_PATH.exists() and str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from src.api.upload_api import router as upload_router
from src.api.chat import router as chat_router
from src.observability.langsmith import tracing_context, _get_client, _get_project_name, is_enabled
from src.observability.telemetry import setup_observability
from src.middleware.rate_limiter import RateLimiterMiddleware, SlidingWindowStore


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

# Configures logging level + (optional) OpenTelemetry span tracing.
# Does NOT add middleware or mount /metrics — Instrumentator and
# LangSmithRequestTracingMiddleware below already own those.
setup_observability(service_name="contract-intelligence-api")

app = FastAPI(
    title="Contract Intelligence Chatbot",
    description="AI-powered contract analysis using Knowledge RAG and Agentic RAG pipelines.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware stack
# ---------------------------------------------------------------------------
# FastAPI applies middleware in *reverse* registration order (LIFO).
# Runtime execution order (outermost → innermost):
#   1. CORSMiddleware          — OPTIONS pre-flights resolved before rate-checking
#   2. RateLimiterMiddleware   — reject abusive clients with HTTP 429
#   3. LangSmithRequestTracingMiddleware — trace allowed requests only
#   4. Prometheus Instrumentator        — counts all responses incl. 429s
# ---------------------------------------------------------------------------

# 4 — registered first → innermost at runtime
app.add_middleware(LangSmithRequestTracingMiddleware)

# Prometheus instrumentator wraps the app core (counts 429s from the limiter).
Instrumentator().instrument(app).expose(app)

# 2 — rate limiter (registered after LangSmith → executes before LangSmith)
_rate_limit_store = SlidingWindowStore()
app.add_middleware(RateLimiterMiddleware, store=_rate_limit_store)

# 1 — CORS registered last → outermost at runtime (handles preflight OPTIONS)
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