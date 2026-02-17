from __future__ import annotations

from fastapi.testclient import TestClient

from linkedwifi_saas.main import app
from linkedwifi_saas import main as main_module


def test_ready_returns_200_when_dependencies_ok(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "_check_database", lambda: True)
    monkeypatch.setattr(main_module, "_check_redis", lambda: True)

    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"


def test_ready_returns_503_when_any_dependency_fails(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "_check_database", lambda: True)
    monkeypatch.setattr(main_module, "_check_redis", lambda: False)

    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "error"
