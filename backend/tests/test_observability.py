from __future__ import annotations

from fastapi.testclient import TestClient

from linkedwifi_saas.main import app


def test_request_id_header_present_on_health_response() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")
