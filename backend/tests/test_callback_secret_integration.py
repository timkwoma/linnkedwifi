from __future__ import annotations

from fastapi.testclient import TestClient

from linkedwifi_saas.database import settings
from linkedwifi_saas.main import app


def test_mpesa_callback_secret_enforced_over_http(monkeypatch) -> None:
    monkeypatch.setattr(
        settings, "mpesa_callback_secret", "integration-secret", raising=False
    )
    client = TestClient(app)

    payload = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": "not-mapped",
                "ResultCode": 0,
            }
        }
    }

    missing_header = client.post("/payments/mpesa/callback", json=payload)
    assert missing_header.status_code == 403
    assert "Invalid callback signature" in missing_header.text

    valid_header = client.post(
        "/payments/mpesa/callback",
        json=payload,
        headers={"X-Callback-Secret": "integration-secret"},
    )
    assert valid_header.status_code == 200
    assert valid_header.json() == {"message": "Payment not mapped"}
