import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).parents[1] / "doc_registry.json"


def _load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load document registry: %s", exc)
        return {}


def _save_registry(registry: dict) -> None:
    try:
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to save document registry: %s", exc)


def register_document(
    doc_id: str,
    filename: str,
    blob_name: str,
    blob_url: str,
    size_bytes: int,
    indexed: bool = True,
) -> dict:
    registry = _load_registry()
    record = {
        "doc_id": doc_id,
        "filename": filename,
        "blob_name": blob_name,
        "blob_url": blob_url,
        "size_bytes": size_bytes,
        "indexed": indexed,
        "deleted": False,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
    }
    registry[doc_id] = record
    _save_registry(registry)
    return record


def update_document(doc_id: str, **updates) -> dict | None:
    registry = _load_registry()
    record = registry.get(doc_id)
    if not record:
        return None
    record.update(updates)
    registry[doc_id] = record
    _save_registry(registry)
    return record


def list_documents() -> list[dict]:
    registry = _load_registry()
    return sorted(registry.values(), key=lambda item: item.get("uploaded_at", ""), reverse=True)


def get_document(doc_id: str) -> dict | None:
    registry = _load_registry()
    return registry.get(doc_id)


def find_by_blob_name(blob_name: str) -> dict | None:
    registry = _load_registry()
    return next((record for record in registry.values() if record.get("blob_name") == blob_name), None)


def delete_document(doc_id: str) -> bool:
    registry = _load_registry()
    if doc_id not in registry:
        return False
    registry[doc_id]["deleted"] = True
    registry[doc_id]["indexed"] = False
    _save_registry(registry)
    return True
