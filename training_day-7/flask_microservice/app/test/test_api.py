# tests/test_api.py
import pytest
from app import create_app

# ── Fixture ───────────────────────────────────────────────────────────────────
@pytest.fixture()
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as c:
        yield c

VALID_PAYLOAD = {
    "model_name": "xgboost-v1",
    "features":   {"age": 32, "income": 75000, "credit_score": 720},
    "threshold":  0.5,
}

# ── Health check ──────────────────────────────────────────────────────────────
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"

# ── POST /predictions — valid payload ────────────────────────────────────────
def test_create_prediction_valid(client):
    r = client.post("/predictions", json=VALID_PAYLOAD)
    assert r.status_code == 201
    body = r.get_json()
    assert "id"         in body
    assert "prediction" in body
    assert body["model_name"] == "xgboost-v1"
    assert body["label"] in ("positive", "negative")

# ── POST /predictions — invalid: missing features ────────────────────────────
def test_create_prediction_missing_features(client):
    r = client.post("/predictions", json={"model_name": "xgboost-v1"})
    assert r.status_code == 422
    body = r.get_json()
    assert body["error"] == "Unprocessable Entity"
    assert "details" in body

# ── POST /predictions — invalid: empty features dict ─────────────────────────
def test_create_prediction_empty_features(client):
    r = client.post("/predictions",
                    json={"model_name": "xgboost-v1", "features": {}})
    assert r.status_code == 422

# ── POST /predictions — invalid: threshold out of range ──────────────────────
def test_create_prediction_bad_threshold(client):
    bad = {**VALID_PAYLOAD, "threshold": 1.5}
    r   = client.post("/predictions", json=bad)
    assert r.status_code == 422

# ── GET /predictions/<id> — exists ───────────────────────────────────────────
def test_get_prediction_found(client):
    created = client.post("/predictions", json=VALID_PAYLOAD).get_json()
    r       = client.get(f"/predictions/{created['id']}")
    assert r.status_code == 200
    assert r.get_json()["id"] == created["id"]

# ── GET /predictions/<id> — not found ────────────────────────────────────────
def test_get_prediction_not_found(client):
    r = client.get("/predictions/nonexistent-id-0000")
    assert r.status_code == 404
    assert r.get_json()["error"] == "Not Found"

# ── Correlation ID is echoed back ─────────────────────────────────────────────
def test_correlation_id_header(client):
    r = client.get("/health", headers={"X-Correlation-ID": "test-123"})
    assert r.headers.get("X-Correlation-ID") == "test-123"
