import uuid
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, HTTPException, status, Request
from src.schema.validation import UploadedFile, UploadResponse
from src.retrival.blob_storage import upload_blob, list_blobs, delete_blob, blob_exists
from docs.parser import PDFParser
from docs.chunking import DocumentChunker
from docs.embedding import OpenAIEmbedder
from docs.vector_store import FAISSVectorStore


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
# Initialize ingestion components
# ------------------------------------------------------------------

parser = PDFParser()

chunker = DocumentChunker()

embedder = OpenAIEmbedder()

vector_store = FAISSVectorStore(
    index_dir="faiss_index",
    embedding_model=embedder.embedding_model,
)


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
                            }
                        },
                    }
                }
            },
            "required": True,
        }
    },
)
async def upload_documents(request: Request) -> UploadResponse:
    form   = await request.form()
    files  = form.getlist("files")

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files were provided.")
    if len(files) > MAX_FILES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum {MAX_FILES} files per request.")

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

            logger.info(
                "Generated %d chunks.",
                len(chunks)
            )

            # ---------------------------------------------------------
            # Step 3 : Store in FAISS
            # ---------------------------------------------------------

            vector_store.add_documents(chunks)

            logger.info(
                "Stored document in FAISS."
            )
            
            # Upload to Azure Blob Storage
            blob_name = f"{stem}_{file_id}.pdf"
            blob_url  = upload_blob(blob_name, data)
            logger.info(f"Uploaded to blob: {blob_url}")

            # Delete local temp file
            temp_path.unlink()
            logger.info(f"Deleted local file: {temp_path}")

            uploaded.append(UploadedFile(
                file_id       = file_id,
                original_name = file.filename,
                blob_url      = blob_url,
                size_bytes    = size,
            ))

        except ValueError as ve:
            errors.append({"filename": file.filename, "reason": str(ve)})

        except Exception as ex:
            logger.error(f"Unexpected error for '{file.filename}': {ex}", exc_info=True)
            errors.append({"filename": file.filename, "reason": "An unexpected error occurred."})

        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            try:
                await file.close()
            except Exception:
                pass

    logger.info(f"Upload complete — {len(uploaded)} succeeded, {len(errors)} failed.")

    return UploadResponse(
        message        = f"{len(uploaded)} file(s) uploaded successfully.",
        uploaded_count = len(uploaded),
        failed_count   = len(errors),
        files          = uploaded,
        errors         = errors,
    )


@router.get("/list", summary="List all PDFs in Azure Blob Storage")
async def list_blobs_in_container():
    blobs = list_blobs()
    return {"count": len(blobs), "files": blobs}


@router.delete("/{blob_name}", summary="Delete a PDF from Azure Blob Storage")
async def delete_blob_file(blob_name: str):
    if not blob_exists(blob_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Blob '{blob_name}' not found.")
    delete_blob(blob_name)
    return {"message": f"'{blob_name}' deleted from blob storage."}
