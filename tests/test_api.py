import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDENTS_DB_PATH", str(tmp_path / "test.db"))
    from app.main import app
    with TestClient(app) as c:
        yield c


STUDENT = {
    "name": "Test Student",
    "date_of_birth": "2004-05-17",
    "email": "test@example.com",
    "course": "Computer Science",
}


def test_full_crud_flow(client):
    r = client.post("/students", json=STUDENT)
    assert r.status_code == 201
    sid = r.json()["id"]

    assert client.get(f"/students/{sid}").json()["name"] == "Test Student"
    assert len(client.get("/students").json()) == 1

    r = client.patch(f"/students/{sid}", json={"course": "Data Science"})
    assert r.status_code == 200 and r.json()["course"] == "Data Science"

    r = client.put(f"/students/{sid}", json={**STUDENT, "name": "Renamed"})
    assert r.json()["name"] == "Renamed"

    assert client.delete(f"/students/{sid}").status_code == 200
    assert client.get(f"/students/{sid}").status_code == 404


def test_missing_record_returns_404(client):
    assert client.get("/students/999").status_code == 404
    assert client.patch("/students/999", json={"name": "X"}).status_code == 404
    assert client.delete("/students/999").status_code == 404


def test_validation(client):
    assert client.post("/students", json={"name": "A", "date_of_birth": "2004-01-01"}).status_code == 422
    assert client.post("/students", json={**STUDENT, "email": "bad"}).status_code == 422
    assert client.post("/students", json={**STUDENT, "date_of_birth": "2999-01-01"}).status_code == 422


def test_duplicate_email(client):
    client.post("/students", json=STUDENT)
    assert client.post("/students", json=STUDENT).status_code == 409


def test_filters(client):
    client.post("/students", json=STUDENT)
    client.post("/students", json={**STUDENT, "name": "Young One", "email": "y@example.com",
                                   "date_of_birth": "2006-01-01", "course": "Electronics"})
    assert len(client.get("/students", params={"course": "Electronics"}).json()) == 1
    assert len(client.get("/students", params={"born_after": "2005-01-01"}).json()) == 1
    assert len(client.get("/students", params={"name": "test"}).json()) == 1


def test_ai_fallback_is_grounded(client, monkeypatch):
    from app import ai
    monkeypatch.setattr(ai, "ask_ollama", lambda prompt: None)
    client.post("/students", json=STUDENT)
    r = client.post("/ai/ask", json={"question": "How many students are there?"})
    assert r.status_code == 200
    assert r.json()["source"] == "fallback"
    assert "1" in r.json()["answer"]
