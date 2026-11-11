"""Tests for liveness and PostgreSQL readiness health endpoints."""

from app.extensions import db


def test_liveness_returns_200(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "alive"
    assert data["service"] == "busreserve-api"
    assert response.headers.get("X-Request-ID")


def test_readiness_returns_200_with_postgres(client):
    response = client.get("/health/ready", headers={"X-Request-ID": "health-trace-001"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert response.headers.get("X-Request-ID") == "health-trace-001"
    assert data["request_id"] == "health-trace-001"


def test_readiness_returns_503_when_database_fails(client, monkeypatch):
    def _broken_execute(*args, **kwargs):
        raise RuntimeError("Simulated PostgreSQL outage")

    monkeypatch.setattr(db.session, "execute", _broken_execute)
    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "not_ready"
    assert data["database"] == "disconnected"
