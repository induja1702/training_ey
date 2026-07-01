"""
Tests for upload_api.py.

These use FastAPI's TestClient (no real server needed — unlike
test_api_upload.py, which hits a live running server over HTTP) and mock
out everything below the route layer: parser, chunker, session_store, and
get_vector_store. This means these tests are fast, free, and don't touch
the filesystem, FAISS, or any real PDF parsing — they test the ROUTE
LOGIC (validation, error handling, response shape), not PDF parsing or
vector store quality.

Run with:
    python -m pytest test/test_upload_api.py -v

Adjust the import path below (`src.api.upload_api`) to match wherever
upload_api.py actually lives in your project.
"""

import io
import sys
import types
import uuid
from unittest.mock import MagicMock

import pytest

# -----------------------------------------------------------------------
# Stub out the heavy modules BEFORE upload_api (or anything it imports)
# gets loaded. docs.chunking pulls in langchain_text_splitters ->
# sentence_transformers -> torch/pyarrow/datasets, which is both slow
# and, in some Windows/conda environments, crashes with a native access
# violation due to OpenMP runtime conflicts between sklearn/pyarrow/torch.
# Tests for upload_api.py's ROUTE LOGIC don't need any of that — they
# mock parser/chunker behavior anyway — so we replace the modules in
# sys.modules with lightweight stand-ins before the real import happens.
# -----------------------------------------------------------------------

_stub_parser_module = types.ModuleType("docs.parser")


class _StubPDFParser:
    def parse(self, pdf_path):
        return ["stub page text"]


_stub_parser_module.PDFParser = _StubPDFParser
sys.modules["docs.parser"] = _stub_parser_module

_stub_chunking_module = types.ModuleType("docs.chunking")


class _StubDocumentChunker:
    def chunk(self, pages, doc_id, filename):
        return [{"text": p, "doc_id": doc_id, "filename": filename} for p in pages]


_stub_chunking_module.DocumentChunker = _StubDocumentChunker
sys.modules["docs.chunking"] = _stub_chunking_module


from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import upload_api  # adjust import path to match your project


# -----------------------------
# Fixtures
# -----------------------------

@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(upload_api.router, prefix="/upload")
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch):
    """Replaces the module-level parser/chunker/session_store/get_vector_store
    that upload_api.py builds at import time, so no real PDF parsing, FAISS,
    or SQLite ever runs during these tests."""

    mock_parser = MagicMock()
    mock_parser.parse.return_value = ["page 1 text"]

    mock_chunker = MagicMock()
    mock_chunker.chunk.return_value = [{"text": "chunk 1"}]

    mock_vector_store = MagicMock()
    mock_get_vector_store = MagicMock(return_value=mock_vector_store)

    mock_session_store = MagicMock()
    mock_session_store.make_session.side_effect = (
        lambda requested_id, reset=False: requested_id or "generated-session-id"
    )
    mock_session_store.session_exists.return_value = True
    mock_session_store.list_documents.return_value = []
    mock_session_store.delete_document.return_value = True

    monkeypatch.setattr(upload_api, "parser", mock_parser)
    monkeypatch.setattr(upload_api, "chunker", mock_chunker)
    monkeypatch.setattr(upload_api, "get_vector_store", mock_get_vector_store)
    monkeypatch.setattr(upload_api, "session_store", mock_session_store)

    return {
        "parser": mock_parser,
        "chunker": mock_chunker,
        "vector_store": mock_vector_store,
        "get_vector_store": mock_get_vector_store,
        "session_store": mock_session_store,
    }


def _pdf_file(filename="contract.pdf", content=b"%PDF-1.4 fake pdf bytes", content_type="application/pdf"):
    return ("files", (filename, io.BytesIO(content), content_type))


# -----------------------------
# POST /upload/ — validation
# -----------------------------

class TestUploadValidation:

    def test_no_files_returns_400(self, client):
        response = client.post("/upload/", files=[])
        assert response.status_code == 400
        assert "No files were provided" in response.json()["detail"]

    def test_too_many_files_returns_400(self, client):
        files = [_pdf_file(filename=f"doc{i}.pdf") for i in range(11)]  # MAX_FILES = 10
        response = client.post("/upload/", files=files)
        assert response.status_code == 400
        assert "Maximum" in response.json()["detail"]

    def test_non_pdf_extension_is_rejected_as_error_not_exception(self, client):
        files = [_pdf_file(filename="notes.txt", content_type="text/plain")]
        response = client.post("/upload/", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["uploaded_count"] == 0
        assert data["failed_count"] == 1
        assert "not a PDF" in data["errors"][0]["reason"]

    def test_unsupported_content_type_is_rejected(self, client):
        files = [_pdf_file(filename="contract.pdf", content_type="image/png")]
        response = client.post("/upload/", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["failed_count"] == 1
        assert "unsupported content type" in data["errors"][0]["reason"]


# -----------------------------
# POST /upload/ — success path
# -----------------------------

class TestUploadSuccess:

    def test_single_valid_pdf_succeeds(self, client, mock_dependencies):
        response = client.post("/upload/", files=[_pdf_file()])
        assert response.status_code == 200
        data = response.json()

        assert data["uploaded_count"] == 1
        assert data["failed_count"] == 0
        assert len(data["files"]) == 1
        assert data["files"][0]["original_name"] == "contract.pdf"
        assert "file_id" in data["files"][0]
        assert data["session_id"]  # a session id was returned

        # Confirm the pipeline was actually invoked
        mock_dependencies["parser"].parse.assert_called_once()
        mock_dependencies["chunker"].chunk.assert_called_once()
        mock_dependencies["vector_store"].add_documents.assert_called_once()
        mock_dependencies["session_store"].add_document.assert_called_once()

    def test_reuses_provided_session_id(self, client, mock_dependencies):
        existing_session = str(uuid.uuid4())
        response = client.post(
            "/upload/",
            files=[_pdf_file()],
            data={"session_id": existing_session},
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == existing_session
        mock_dependencies["session_store"].make_session.assert_called_once_with(
            existing_session, reset=False
        )

    def test_multiple_files_mixed_success_and_failure(self, client, mock_dependencies):
        files = [
            _pdf_file(filename="good.pdf"),
            _pdf_file(filename="bad.txt", content_type="text/plain"),
        ]
        response = client.post("/upload/", files=files)
        data = response.json()
        assert data["uploaded_count"] == 1
        assert data["failed_count"] == 1
        assert data["files"][0]["original_name"] == "good.pdf"
        assert data["errors"][0]["filename"] == "bad.txt"


# -----------------------------
# POST /upload/ — error handling inside the pipeline
# -----------------------------

class TestUploadPipelineErrors:

    def test_zero_chunks_is_reported_as_error_not_silent_success(self, client, mock_dependencies):
        mock_dependencies["chunker"].chunk.return_value = []
        response = client.post("/upload/", files=[_pdf_file()])
        data = response.json()
        assert data["uploaded_count"] == 0
        assert data["failed_count"] == 1
        assert "0 chunks" in data["errors"][0]["reason"]

    def test_unexpected_parser_exception_is_caught_and_reported(self, client, mock_dependencies):
        mock_dependencies["parser"].parse.side_effect = RuntimeError("corrupted PDF stream")
        response = client.post("/upload/", files=[_pdf_file()])
        assert response.status_code == 200  # caught, not propagated as 500
        data = response.json()
        assert data["uploaded_count"] == 0
        assert data["failed_count"] == 1
        assert data["errors"][0]["reason"] == "An unexpected error occurred."


# -----------------------------
# GET /upload/list/{session_id}
# -----------------------------

class TestListSessionUploads:

    def test_unknown_session_returns_404(self, client, mock_dependencies):
        mock_dependencies["session_store"].session_exists.return_value = False
        response = client.get("/upload/list/some-session-id")
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]

    def test_known_session_returns_documents(self, client, mock_dependencies):
        mock_dependencies["session_store"].list_documents.return_value = [
            {"file_id": "f1", "original_name": "a.pdf"}
        ]
        response = client.get("/upload/list/some-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "some-session-id"
        assert data["count"] == 1
        assert data["files"][0]["original_name"] == "a.pdf"

    def test_trailing_period_in_session_id_is_stripped(self, client, mock_dependencies):
        """Regression test: a stray trailing '.' in the URL (e.g. from a
        client-side templating bug) should not cause a false 404 — the
        route strips trailing punctuation before checking session_exists."""
        response = client.get("/upload/list/some-session-id.")
        assert response.status_code == 200
        # session_exists should have been called with the STRIPPED id
        mock_dependencies["session_store"].session_exists.assert_called_with("some-session-id")
        assert response.json()["session_id"] == "some-session-id"


# -----------------------------
# DELETE /upload/{session_id}/{file_id}
# -----------------------------

class TestDeleteSessionDocument:

    def test_delete_missing_document_returns_404(self, client, mock_dependencies):
        mock_dependencies["session_store"].delete_document.return_value = False
        response = client.delete("/upload/session-1/file-1")
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]

    def test_delete_existing_document_succeeds(self, client, mock_dependencies):
        mock_dependencies["session_store"].delete_document.return_value = True
        response = client.delete("/upload/session-1/file-1")
        assert response.status_code == 200
        assert "removed from session" in response.json()["message"]
        mock_dependencies["session_store"].delete_document.assert_called_once_with(
            "session-1", "file-1"
        )


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))