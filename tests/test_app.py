"""
Automated tests for the Task Management API.

The database layer is monkeypatched with an in-memory fake so these tests
run anywhere (locally, in Docker, in GitHub Actions) without requiring a
live PostgreSQL instance. This keeps the suite fast and deterministic while
still exercising the real Flask routes, validation, and error handling.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as app_module  # noqa: E402


class FakeDB:
    """A tiny in-memory stand-in for the database module."""

    def __init__(self):
        self.tasks = {}
        self.next_id = 1
        self.connected = True

    def reset(self):
        self.tasks = {}
        self.next_id = 1
        self.connected = True

    def check_connection(self):
        return self.connected

    def fetch_all_tasks(self):
        return [self.tasks[i] for i in sorted(self.tasks)]

    def fetch_task(self, task_id):
        return self.tasks.get(task_id)

    def create_task(self, title, description, status):
        task = {
            "id": self.next_id,
            "title": title,
            "description": description,
            "status": status,
        }
        self.tasks[self.next_id] = task
        self.next_id += 1
        return task

    def update_task(self, task_id, title, description, status):
        if task_id not in self.tasks:
            return None
        task = {"id": task_id, "title": title, "description": description, "status": status}
        self.tasks[task_id] = task
        return task

    def delete_task(self, task_id):
        return self.tasks.pop(task_id, None) is not None


fake_db = FakeDB()


@pytest.fixture(autouse=True)
def patch_database(monkeypatch):
    fake_db.reset()
    monkeypatch.setattr(app_module.database, "check_connection", fake_db.check_connection)
    monkeypatch.setattr(app_module.database, "fetch_all_tasks", fake_db.fetch_all_tasks)
    monkeypatch.setattr(app_module.database, "fetch_task", fake_db.fetch_task)
    monkeypatch.setattr(app_module.database, "create_task", fake_db.create_task)
    monkeypatch.setattr(app_module.database, "update_task", fake_db.update_task)
    monkeypatch.setattr(app_module.database, "delete_task", fake_db.delete_task)
    yield


@pytest.fixture
def client():
    app_module.app.testing = True
    return app_module.app.test_client()


# --- Basic endpoints -----------------------------------------------------

def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "running"
    assert "application" in body
    assert "version" in body


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "healthy"}


def test_db_health_connected(client):
    fake_db.connected = True
    resp = client.get("/db-health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "healthy", "database": "connected"}


def test_db_health_disconnected(client):
    fake_db.connected = False
    resp = client.get("/db-health")
    assert resp.status_code == 503
    assert resp.get_json() == {"status": "unhealthy", "database": "disconnected"}


# --- Task creation ---------------------------------------------------------

def test_create_task(client):
    resp = client.post("/tasks", json={"title": "Learn Kubernetes", "description": "Practice"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "Learn Kubernetes"
    assert body["status"] == "pending"
    assert "id" in body


def test_create_task_invalid_missing_title(client):
    resp = client.post("/tasks", json={"description": "no title here"})
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "title is required"}


def test_create_task_invalid_empty_title(client):
    resp = client.post("/tasks", json={"title": "   "})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "title is required"


def test_create_task_invalid_status(client):
    resp = client.post("/tasks", json={"title": "Task", "status": "bogus"})
    assert resp.status_code == 400
    assert "status" in resp.get_json()["error"]


def test_create_task_title_too_long(client):
    resp = client.post("/tasks", json={"title": "x" * 201})
    assert resp.status_code == 400


# --- Task retrieval ---------------------------------------------------------

def test_get_task(client):
    created = client.post("/tasks", json={"title": "Task A"}).get_json()
    resp = client.get(f"/tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Task A"


def test_get_task_not_found(client):
    resp = client.get("/tasks/9999")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Task not found"}


def test_list_tasks(client):
    client.post("/tasks", json={"title": "Task A"})
    client.post("/tasks", json={"title": "Task B"})
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


# --- Task update ---------------------------------------------------------

def test_update_task(client):
    created = client.post("/tasks", json={"title": "Old title"}).get_json()
    resp = client.put(
        f"/tasks/{created['id']}",
        json={"title": "New title", "description": "Updated", "status": "completed"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New title"
    assert body["status"] == "completed"


def test_update_task_not_found(client):
    resp = client.put("/tasks/9999", json={"title": "Doesn't matter"})
    assert resp.status_code == 404


def test_update_task_invalid_status(client):
    created = client.post("/tasks", json={"title": "Task"}).get_json()
    resp = client.put(f"/tasks/{created['id']}", json={"title": "Task", "status": "bogus"})
    assert resp.status_code == 400


# --- Task deletion ---------------------------------------------------------

def test_delete_task(client):
    created = client.post("/tasks", json={"title": "Delete me"}).get_json()
    resp = client.delete(f"/tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == {"message": "Task deleted successfully"}

    resp2 = client.get(f"/tasks/{created['id']}")
    assert resp2.status_code == 404


def test_delete_task_not_found(client):
    resp = client.delete("/tasks/9999")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "Task not found"}
