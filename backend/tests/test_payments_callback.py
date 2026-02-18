from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from linkedwifi_saas.models import PaymentStatus
from linkedwifi_saas.routers import payments as payments_router


def test_mpesa_callback_rejects_missing_callback_secret_when_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    monkeypatch.setattr(
        payments_router.settings, "mpesa_callback_secret", "topsecret", raising=False
    )
    with pytest.raises(HTTPException) as exc:
        payments_router.mpesa_callback(
            {"Body": {"stkCallback": {"CheckoutRequestID": "abc", "ResultCode": 0}}},
            db,
            callback_secret=None,
        )
    assert exc.value.status_code == 403


def test_mpesa_callback_rejects_invalid_callback_secret_when_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    monkeypatch.setattr(
        payments_router.settings, "mpesa_callback_secret", "topsecret", raising=False
    )
    with pytest.raises(HTTPException) as exc:
        payments_router.mpesa_callback(
            {"Body": {"stkCallback": {"CheckoutRequestID": "abc", "ResultCode": 0}}},
            db,
            callback_secret="wrong",
        )
    assert exc.value.status_code == 403


def test_mpesa_callback_allows_valid_callback_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    payment = SimpleNamespace(status=PaymentStatus.success)
    db.scalar.return_value = payment
    monkeypatch.setattr(
        payments_router.settings, "mpesa_callback_secret", "topsecret", raising=False
    )

    result = payments_router.mpesa_callback(
        {"Body": {"stkCallback": {"CheckoutRequestID": "abc", "ResultCode": 0}}},
        db,
        callback_secret="topsecret",
    )
    assert result == {"result": "ignored", "reason": "already_processed"}


def test_mpesa_callback_rejects_invalid_payload() -> None:
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        payments_router.mpesa_callback(
            {"Body": {"stkCallback": {"CheckoutRequestID": "abc"}}}, db
        )
    assert exc.value.status_code == 400


def test_mpesa_callback_is_idempotent_for_processed_payment() -> None:
    db = MagicMock()
    payment = SimpleNamespace(status=PaymentStatus.success)
    db.scalar.return_value = payment

    payload = {"Body": {"stkCallback": {"CheckoutRequestID": "abc", "ResultCode": 0}}}
    result = payments_router.mpesa_callback(payload, db)

    assert result == {"result": "ignored", "reason": "already_processed"}
    db.commit.assert_not_called()


def test_mpesa_callback_success_marks_payment_and_activates_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    payment = SimpleNamespace(
        status=PaymentStatus.pending,
        tenant_id=uuid4(),
        user_id=uuid4(),
        package_id=uuid4(),
        phone="+254700000002",
        mpesa_receipt=None,
    )
    db.scalar.return_value = payment

    calls: list[dict] = []

    def _fake_session_activation(*args, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        payments_router, "create_session_after_payment", _fake_session_activation
    )

    payload = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": "abc",
                "ResultCode": 0,
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "MpesaReceiptNumber", "Value": "R123XYZ"},
                        {"Name": "ClientMAC", "Value": "AA:BB:CC:DD:EE:FF"},
                        {"Name": "ClientIP", "Value": "10.0.0.10"},
                    ]
                },
            }
        }
    }
    result = payments_router.mpesa_callback(payload, db)

    assert result == {"result": "ok"}
    assert payment.status == PaymentStatus.success
    assert payment.mpesa_receipt == "R123XYZ"
    assert len(calls) == 1
    db.commit.assert_called_once()
