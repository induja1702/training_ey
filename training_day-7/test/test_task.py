
import pytest

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────

@pytest.fixture
def sample_task():
    return {"title": "Buy milk", "priority": "high"}


@pytest.fixture
def created_task(sample_task):
    res = client.post("/tasks", json=sample_task)

    return res.json()


# ── Tests ─────────────────────────────────────────────

def test_create_task(sample_task):
    res = client.post("/tasks", json=sample_task)

    assert res.status_code == 201

    data = res.json()

    assert data["title"] == sample_task["title"]

    assert "id" in data


def test_get_task(created_task):
    task_id = created_task["id"]

    res = client.get(f"/tasks/{task_id}")

    assert res.status_code == 200


def test_create_task_validation():
    res = client.post("/tasks", json={"title": ""})

    assert res.status_code == 422  # Pydantic validation error