import uuid
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, HTTPException, status, Request
from src.schema.validation import UploadedFile, UploadResponse
from src.retrival.blob_storage import upload_blob, list_blobs, delete_blob, blob_exists
from src.orchestator.session_store import session_store          # adjust import path to match your project
from src.orchestator.vector_store_manager import get_vector_store  # adjust import path to match your project
from docs.parser import PDFParser
from docs.chunking import DocumentChunker

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TEMP_DIR              = Path("temp_uploads")
ALLOWED_EXTENSIONS    = {".pdf"}
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream", "binary/octet-stream"}
MAX_FILE_SIZE_MB      = 50
MAX_FILE_SIZE         = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_FILES             = 10

TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Initialize ingestion components (vector_store is now per-session,
# see vector_store_manager.get_vector_store(session_id) below)
# ------------------------------------------------------------------

parser = PDFParser()
chunker = DocumentChunker()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_file(file: UploadFile) -> str | None:
    if not file.filename:
        return "Filename is missing."
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return f"'{file.filename}' is not a PDF. Only .pdf files are accepted."
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        return (
            f"'{file.filename}' has unsupported content type: {file.content_type}."
        )
    return None


async def read_upload(file: UploadFile) -> tuple[bytes, int]:
    data = b""
    while chunk := await file.read(1024 * 1024):
        data += chunk
        if len(data) > MAX_FILE_SIZE:
            raise ValueError(f"'{file.filename}' exceeds the {MAX_FILE_SIZE_MB} MB limit.")
    return data, len(data)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    openapi_extra={
        "requestBody": {
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["files"],
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {"type": "string", "format": "binary"},
                                "description": "One or more PDF files",
                            },
                            "session_id": {
                                "type": "string",
                                "description": (
                                    "Existing chat session to attach these documents to. "
                                    "Omit to start a brand-new session."
                                ),
                            },
                        },
                    }
                }
            },
            "required": True,
        }
    },
)
async def upload_documents(request: Request) -> UploadResponse:
    form  = await request.form()
    files = form.getlist("files")
    requested_session_id = form.get("session_id")  # may be None on first upload of a new chat

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files were provided.")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum {MAX_FILES} files per request.")

    # Reuse the given session if it exists, otherwise mint a new one.
    # This is the same session_id the client will later pass to /chat/.
    session_id = session_store.make_session(requested_session_id, reset=False)
    vector_store = get_vector_store(session_id)

    uploaded: List[UploadedFile] = []
    errors:   List[dict]         = []

    for file in files:
        temp_path: Path | None = None
        try:
            err = validate_file(file)
            if err:
                errors.append({"filename": file.filename, "reason": err})
                continue

            data, size = await read_upload(file)

            # Save locally
            file_id   = str(uuid.uuid4())
            stem      = Path(file.filename).stem
            temp_path = TEMP_DIR / f"{stem}_{file_id}.pdf"
            temp_path.write_bytes(data)
            logger.info(f"Saved locally: {temp_path} ({size:,} bytes)")
            TEMP_DIR.mkdir(parents=True, exist_ok=True)

            # # ---------------------------------------------------------
            # # Step 1 : Parse PDF
            # # ---------------------------------------------------------
            pages = parser.parse(pdf_path=temp_path)
            logger.info(f"Parsed {len(pages)} pages.")
            #
            # ---------------------------------------------------------
            # Step 2 : Chunk PDF
            # ---------------------------------------------------------
            chunks = chunker.chunk(
                pages=pages,
                doc_id=file_id,
                filename=file.filename,
            )
            logger.info("Generated %d chunks.", len(chunks))

            if not chunks:
                # No text could be extracted from any page, even after the
                # OCR fallback in parser.py. Surface this as a real error
                # instead of silently "succeeding" with nothing indexed.
                raise ValueError(
                    f"'{file.filename}' produced 0 chunks — no extractable text was "
                    "found on any page, even after OCR. The file may be scanned at "
                    "very low quality, password-protected/encrypted, or corrupted. "
                    "Check server logs for the OCR fallback details."
                )

            # ---------------------------------------------------------
            # Step 3 : Store in this session's own FAISS index
            # ---------------------------------------------------------

            vector_store.add_documents(chunks)

            # ---------------------------------------------------------
            # Step 4 : Record the document against this session in SQLite,
            # so /chat/, /documents, and history all agree on what's in
            # this chat.
            # ---------------------------------------------------------
            session_store.add_document(
                session_id=session_id,
                file_id=file_id,
                original_name=file.filename,
                size_bytes=size,
            )
            
            # # Upload to Azure Blob Storage
            # blob_name = f"{stem}_{file_id}.pdf"
            # blob_url  = upload_blob(blob_name, data)
            # logger.info(f"Uploaded to blob: {blob_url}")

            # # Delete local temp file
            # temp_path.unlink()
            # logger.info(f"Deleted local file: {temp_path}")

            uploaded.append(UploadedFile(
                file_id       = file_id,
                original_name = file.filename,
                # blob_url      = blob_url,
                size_bytes    = size,
            ))

        except ValueError as ve:
            errors.append({"filename": file.filename, "reason": str(ve)})

        except Exception as ex:
            logger.error(f"Unexpected error for '{file.filename}': {ex}", exc_info=True)
            errors.append({"filename": file.filename, "reason": "An unexpected error occurred."})

        # finally:
        #     if temp_path and temp_path.exists():
        #         temp_path.unlink(missing_ok=True)
        #     try:
        #         await file.close()
        #     except Exception:
        #         pass

    logger.info(f"Upload complete — {len(uploaded)} succeeded, {len(errors)} failed.")

    return UploadResponse(
        session_id     = session_id,
        message        = f"{len(uploaded)} file(s) uploaded successfully.",
        uploaded_count = len(uploaded),
        failed_count   = len(errors),
        files          = uploaded,
        errors         = errors,
    )


@router.get("/list/{session_id}", summary="List documents uploaded within a chat session")
async def list_session_uploads(session_id: str):
    """Return the documents that belong to this specific chat session (from SQLite),
    not a directory scan — this is what keeps /chat/ and /upload/ in agreement."""
    session_id = session_id.strip().rstrip(".")
    if not session_store.session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    docs = session_store.list_documents(session_id)
    return {"session_id": session_id, "count": len(docs), "files": docs}


@router.delete("/{session_id}/{file_id}", summary="Remove a document from a chat session")
async def delete_session_document(session_id: str, file_id: str):
    if not session_store.delete_document(session_id, file_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in this session.")
    # NOTE: this removes the SQLite record. If your FAISSVectorStore supports
    # deleting by doc_id, call it here too (e.g. vector_store.delete(file_id))
    # so the embeddings don't linger in the index after the record is gone.
    return {"message": f"Document '{file_id}' removed from session '{session_id}'."}