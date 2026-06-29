import uuid
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from markdown_it.presets import default

from src.schema.validation import UploadedFile, UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TEMP_DIR          = Path("temp_uploads")
ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream", "binary/octet-stream"}
MAX_FILE_SIZE_MB  = 50
MAX_FILE_SIZE     = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_FILES         = 10

TEMP_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def validate_file(file: UploadFile) -> str | None:
    """Return an error message if the file is invalid, else None."""
    if not file.filename:
        return "Filename is missing."

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return f"'{file.filename}' is not a PDF. Only .pdf files are accepted."

    # content_type check is lenient — some clients send octet-stream for PDFs
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        return (
            f"'{file.filename}' has an unsupported content type: {file.content_type}. "
            "Expected application/pdf."
        )

    return None


def save_file(file: UploadFile) -> UploadedFile:
    """Stream the upload to temp_uploads/. Raises ValueError if file is too large."""
    file_id   = str(uuid.uuid4())
    stem      = Path(file.filename).stem
    save_path = TEMP_DIR / f"{stem}_{file_id}.pdf"

    size = 0
    with open(save_path, "wb") as out:
        while chunk := file.file.read(1024 * 1024):  # stream in 1 MB chunks
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                out.close()
                save_path.unlink(missing_ok=True)
                raise ValueError(
                    f"'{file.filename}' exceeds the {MAX_FILE_SIZE_MB} MB limit."
                )
            out.write(chunk)

    logger.info(f"Saved '{file.filename}' → {save_path} ({size:,} bytes)")

    return UploadedFile(
        file_id       = file_id,
        original_name = file.filename,
        saved_path    = str(save_path),
        size_bytes    = size,
    )


# ---------------------------------------------------------------------------
# Routes
# Note: prefix="/upload" is set in main.py — do NOT repeat it here.
# Final URLs:
#   POST   /upload/         → upload_documents
#   GET    /upload/list     → list_temp_files
#   DELETE /upload/clear    → clear_temp_folder
#   DELETE /upload/{file_id}→ delete_temp_file
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=UploadResponse,
)
async def upload_documents(
        files: List[UploadFile] = File(
            ...,
            description="One or more PDF files"
        )) -> UploadResponse:

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were provided.",
        )

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_FILES} files per request.",
        )

    uploaded: List[UploadedFile] = []
    errors:   List[dict]         = []

    for file in files:
        # Step 1 — validate
        err = validate_file(file)
        if err:
            logger.warning(f"Validation failed for '{file.filename}': {err}")
            errors.append({"filename": file.filename, "reason": err})
            continue

        # Step 2 — save to temp
        try:
            result = save_file(file)
            uploaded.append(result)

            # TODO: trigger ingestion pipeline once Person A implements it
            # background_tasks.add_task(ingestion_pipeline.run, result.saved_path, result.file_id)

        except ValueError as ve:
            logger.warning(str(ve))
            errors.append({"filename": file.filename, "reason": str(ve)})

        except Exception as ex:
            logger.error(
                f"Unexpected error saving '{file.filename}': {ex}", exc_info=True
            )
            errors.append({
                "filename": file.filename,
                "reason":   "An unexpected error occurred while saving the file.",
            })

        finally:
            await file.close()

    logger.info(f"Upload complete — {len(uploaded)} succeeded, {len(errors)} failed.")

    return UploadResponse(
        message        = f"{len(uploaded)} file(s) uploaded successfully.",
        uploaded_count = len(uploaded),
        failed_count   = len(errors),
        files          = uploaded,
        errors         = errors,
    )


@router.get("/list", summary="List files in the temp upload folder")
async def list_temp_files():
    files = [
        {
            "filename":   f.name,
            "size_bytes": f.stat().st_size,
            "path":       str(f),
        }
        for f in sorted(TEMP_DIR.glob("*.pdf"))
    ]
    return {"temp_dir": str(TEMP_DIR), "count": len(files), "files": files}


@router.delete("/clear", summary="Clear all files from the temp folder")
async def clear_temp_folder():
    files = list(TEMP_DIR.glob("*.pdf"))
    for f in files:
        f.unlink()
    logger.info(f"Cleared {len(files)} file(s) from {TEMP_DIR}.")
    return {"message": f"Cleared {len(files)} file(s) from the temp folder."}


@router.delete("/{file_id}", summary="Delete a specific temp file by file_id")
async def delete_temp_file(file_id: str):
    matches = list(TEMP_DIR.glob(f"*_{file_id}.pdf"))
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No file found with file_id '{file_id}'.",
        )
    for f in matches:
        f.unlink()
        logger.info(f"Deleted temp file: {f}")
    return {"message": f"Deleted {len(matches)} file(s) with file_id '{file_id}'."}