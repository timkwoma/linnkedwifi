from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from linkedwifi_saas.models import Role
from linkedwifi_saas.routers import auth as auth_router
from linkedwifi_saas.schemas import OTPRequestIn, OTPVerifyIn
from linkedwifi_saas.utils.otp import hash_otp


def _request_with_ip(ip: str) -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host=ip))


def test_request_otp_rate_limit_per_phone() -> None:
    auth_router._ip_request_times.clear()
    db = MagicMock()
    db.scalars.return_value.all.return_value = [
        object()
    ] * auth_router.OTP_REQUEST_LIMIT_PER_PHONE

    payload = OTPRequestIn(
        phone="+254700000002",
        role=Role.isp_admin,
        tenant_id=uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        auth_router.request_otp(payload, _request_with_ip("127.0.0.1"), db)

    assert exc.value.status_code == 429
    assert "Too many OTP requests" in exc.value.detail


def test_verify_otp_lock_active_blocks_attempt() -> None:
    db = MagicMock()
    now = datetime.now(timezone.utc)
    otp = SimpleNamespace(
        lock_until=now + timedelta(minutes=5),
        expires_at=now + timedelta(minutes=5),
        failed_attempts=auth_router.OTP_VERIFY_MAX_FAILED_ATTEMPTS,
        code_hash=hash_otp("123456"),
        used=False,
    )
    db.scalar.return_value = otp

    payload = OTPVerifyIn(
        phone="+254700000002",
        role=Role.isp_admin,
        tenant_id=uuid4(),
        code="000000",
    )

    with pytest.raises(HTTPException) as exc:
        auth_router.verify_otp_code(payload, db)

    assert exc.value.status_code == 429
    db.commit.assert_not_called()


def test_verify_otp_reaches_lock_threshold() -> None:
    db = MagicMock()
    now = datetime.now(timezone.utc)
    otp = SimpleNamespace(
        lock_until=None,
        expires_at=now + timedelta(minutes=5),
        failed_attempts=auth_router.OTP_VERIFY_MAX_FAILED_ATTEMPTS - 1,
        code_hash=hash_otp("123456"),
        used=False,
    )
    db.scalar.return_value = otp

    payload = OTPVerifyIn(
        phone="+254700000002",
        role=Role.isp_admin,
        tenant_id=uuid4(),
        code="000000",
    )

    with pytest.raises(HTTPException) as exc:
        auth_router.verify_otp_code(payload, db)

    assert exc.value.status_code == 429
    assert otp.failed_attempts == auth_router.OTP_VERIFY_MAX_FAILED_ATTEMPTS
    assert otp.lock_until is not None
    db.commit.assert_called_once()


def test_verify_otp_invalid_code_increments_attempts() -> None:
    db = MagicMock()
    now = datetime.now(timezone.utc)
    otp = SimpleNamespace(
        lock_until=None,
        expires_at=now + timedelta(minutes=5),
        failed_attempts=0,
        code_hash=hash_otp("123456"),
        used=False,
    )
    db.scalar.return_value = otp

    payload = OTPVerifyIn(
        phone="+254700000002",
        role=Role.isp_admin,
        tenant_id=uuid4(),
        code="000000",
    )

    with pytest.raises(HTTPException) as exc:
        auth_router.verify_otp_code(payload, db)

    assert exc.value.status_code == 400
    assert otp.failed_attempts == 1
    assert otp.lock_until is None
    db.commit.assert_called_once()
