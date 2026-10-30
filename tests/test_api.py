import os

import pytest


def test_01_health_is_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_02_ready_reports_database_up(client):
    r = client.get("/readiness")
    assert r.status_code == 200
    assert r.json()["database"] == "up"
    assert client.get("/ready").status_code == 200  # alias


def test_03_create_incident(client):
    r = client.post("/api/v1/incidents", json={"title": "Disk 90% on node-1", "severity": "high"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "open" and body["id"] == 1


def test_04_list_incidents(client):
    client.post("/api/v1/incidents", json={"title": "Latency spike", "severity": "medium"})
    client.post("/api/v1/incidents", json={"title": "Cert expiring", "severity": "low"})
    r = client.get("/api/v1/incidents")
    assert r.status_code == 200 and len(r.json()) == 2


def test_05_unknown_incident_returns_404(client):
    assert client.get("/api/v1/incidents/999").status_code == 404


def test_06_invalid_severity_rejected(client):
    r = client.post("/api/v1/incidents", json={"title": "Bad input", "severity": "banana"})
    assert r.status_code == 422


def test_07_resolve_incident(client):
    client.post("/api/v1/incidents", json={"title": "Queue backlog", "severity": "critical"})
    r = client.post("/api/v1/incidents/1/resolve")
    assert r.status_code == 200 and r.json()["status"] == "resolved"


def test_08_metrics_exposed(client):
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "apex_http_requests_total" in r.text


def test_09_request_id_header_returned(client):
    r = client.get("/health", headers={"x-request-id": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"


def test_11_update_incident(client):
    client.post("/api/v1/incidents", json={"title": "Old title", "severity": "low"})
    r = client.put("/api/v1/incidents/1", json={"title": "New title", "severity": "high"})
    assert r.status_code == 200
    assert r.json()["title"] == "New title" and r.json()["severity"] == "high"


def test_12_delete_incident(client):
    client.post("/api/v1/incidents", json={"title": "To delete", "severity": "low"})
    assert client.delete("/api/v1/incidents/1").status_code == 204
    assert client.get("/api/v1/incidents/1").status_code == 404
    assert client.delete("/api/v1/incidents/1").status_code == 404


def test_13_readiness_returns_503_when_database_down(client, monkeypatch):
    from app.db import get_db
    from app.main import app as fastapi_app

    class BrokenSession:
        def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    fastapi_app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        r = client.get("/readiness")
        assert r.status_code == 503
        assert r.json()["database"] == "down"
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.mark.skipif(
    os.getenv("INTENTIONAL_FAILURE") != "1",
    reason="Demo gate: set INTENTIONAL_FAILURE=1 to prove CI blocks deployment",
)
def test_10_intentional_failure_demo(client):
    """Fails on purpose when INTENTIONAL_FAILURE=1 (used to show the CI gate)."""
    assert client.get("/health").json()["status"] == "broken-on-purpose"
