# app/routes/predictions.py
from flask          import Blueprint, request, jsonify
from pydantic       import ValidationError
from app.handlers.models     import PredictionRequest, PredictionResponse
from app.handlers.logging_config import logger
import uuid, random

bp = Blueprint("predictions", __name__)

# In-memory store (replace with DB in production)
_store: dict[str, dict] = {}

def _safe_errors(exc: ValidationError) -> list:
    """Make pydantic errors JSON-serializable (ctx may hold raw Exception)."""
    return [
        {k: (str(v) if k == "ctx" else v) for k, v in e.items()}
        for e in exc.errors()
    ]

# ── POST /predictions ─────────────────────────────────────────────────────────
@bp.route("/predictions", methods=["POST"])
def create_prediction():
    try:
        body = PredictionRequest.model_validate(request.get_json(force=True) or {})
    except ValidationError as exc:
        safe = _safe_errors(exc)
        logger.warning("validation_failed", errors=safe)
        return jsonify({"error": "Unprocessable Entity", "details": safe}), 422

    score  = round(random.uniform(0.0, 1.0), 4)
    label  = "positive" if score >= body.threshold else "negative"

    resp = PredictionResponse(
        model_name = body.model_name,
        prediction = score,
        label      = label,
        confidence = round(abs(score - 0.5) * 2, 4),
        threshold  = body.threshold,
    )
    _store[resp.id] = resp.model_dump(mode="json")
    logger.info("prediction_created", id=resp.id, label=label, score=score)
    return jsonify(_store[resp.id]), 201

# ── GET /predictions/<id> ─────────────────────────────────────────────────────
@bp.route("/predictions/<string:pred_id>", methods=["GET"])
def get_prediction(pred_id: str):
    record = _store.get(pred_id)
    if not record:
        logger.warning("prediction_not_found", id=pred_id)
        return jsonify({"error": "Not Found",
                        "message": f"No prediction with id={pred_id}"}), 404
    return jsonify(record), 200

# ── GET /health ───────────────────────────────────────────────────────────────
@bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok",
                    "predictions_stored": len(_store)}), 200
