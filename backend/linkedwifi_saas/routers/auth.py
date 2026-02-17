from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..database import get_db, settings
from ..models import Account, OTPCode, Role, User
from ..schemas import AuthTokenOut, OTPRequestIn, OTPVerifyIn
from ..security import create_access_token
from ..utils.otp import generate_otp, hash_otp, otp_expiry, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])

OTP_REQUEST_LIMIT_PER_PHONE = 5
OTP_REQUEST_PHONE_WINDOW_SECONDS = 600
OTP_REQUEST_LIMIT_PER_IP = 30
OTP_REQUEST_IP_WINDOW_SECONDS = 60
OTP_VERIFY_MAX_FAILED_ATTEMPTS = 5
OTP_VERIFY_LOCK_SECONDS = 300

_ip_request_times: dict[str, deque[datetime]] = defaultdict(deque)
_ip_limiter_lock = Lock()


def _normalize_ip(value: str | None) -> str:
    if not value:
        return "unknown"
    return value.strip() or "unknown"


def _enforce_otp_request_limits(
    db: Session,
    *,
    phone: str,
    role: Role,
    tenant_id,
    client_ip: str,
) -> None:
    now = datetime.now(timezone.utc)
    phone_cutoff = now.timestamp() - OTP_REQUEST_PHONE_WINDOW_SECONDS
    ip_cutoff = now.timestamp() - OTP_REQUEST_IP_WINDOW_SECONDS

    recent_phone_requests = db.scalars(
        select(OTPCode)
        .where(
            and_(
                OTPCode.phone == phone,
                OTPCode.role == role,
                OTPCode.tenant_id == tenant_id,
                OTPCode.created_at >= datetime.fromtimestamp(phone_cutoff, timezone.utc),
            )
        )
        .order_by(OTPCode.created_at.desc())
    ).all()
    if len(recent_phone_requests) >= OTP_REQUEST_LIMIT_PER_PHONE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Try again later.",
        )

    # Best-effort per-instance IP throttling for local/dev usage.
    with _ip_limiter_lock:
        ip_requests = _ip_request_times[client_ip]
        while ip_requests and ip_requests[0].timestamp() < ip_cutoff:
            ip_requests.popleft()
        if len(ip_requests) >= OTP_REQUEST_LIMIT_PER_IP:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests from this IP. Try again later.",
            )
        ip_requests.append(now)


@router.post("/request-otp")
def request_otp(payload: OTPRequestIn, request: Request, db: Session = Depends(get_db)) -> dict:
    if payload.role in (Role.user, Role.isp_admin) and not payload.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id is required")
    if payload.role == Role.super_admin and payload.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="super_admin must not send tenant_id",
        )

    _enforce_otp_request_limits(
        db,
        phone=payload.phone,
        role=payload.role,
        tenant_id=payload.tenant_id,
        client_ip=_normalize_ip(request.client.host if request.client else None),
    )

    if payload.role == Role.user:
        user = db.scalar(
            select(User).where(
                and_(User.tenant_id == payload.tenant_id, User.phone == payload.phone)
            )
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not registered")
    else:
        account = db.scalar(
            select(Account).where(
                and_(
                    Account.phone == payload.phone,
                    Account.role == payload.role,
                    Account.tenant_id == payload.tenant_id,
                )
            )
        )
        if not account:
            raise HTTPException(status_code=404, detail="Account not registered")

    code = generate_otp()
    otp = OTPCode(
        tenant_id=payload.tenant_id,
        phone=payload.phone,
        role=payload.role,
        code_hash=hash_otp(code),
        expires_at=otp_expiry(settings.otp_expiry_seconds),
    )
    db.add(otp)
    db.commit()

    # For local development visibility. Replace with SMS provider in production.
    return {"message": "OTP generated", "dev_otp": code}


@router.post("/verify-otp", response_model=AuthTokenOut)
def verify_otp_code(payload: OTPVerifyIn, db: Session = Depends(get_db)) -> AuthTokenOut:
    otp = db.scalar(
        select(OTPCode)
        .where(
            and_(
                OTPCode.phone == payload.phone,
                OTPCode.role == payload.role,
                OTPCode.tenant_id == payload.tenant_id,
                OTPCode.used.is_(False),
            )
        )
        .order_by(OTPCode.created_at.desc())
    )
    if not otp:
        raise HTTPException(status_code=400, detail="OTP not found")

    now = datetime.now(timezone.utc)
    if otp.lock_until is not None:
        lock_until = otp.lock_until if otp.lock_until.tzinfo else otp.lock_until.replace(tzinfo=timezone.utc)
        if lock_until > now:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many invalid OTP attempts. Try again later.",
            )

    if otp.expires_at.tzinfo is None:
        otp_exp = otp.expires_at.replace(tzinfo=timezone.utc)
    else:
        otp_exp = otp.expires_at
    if otp_exp < now:
        raise HTTPException(status_code=400, detail="OTP expired")
    if not verify_otp(payload.code, otp.code_hash):
        otp.failed_attempts += 1
        if otp.failed_attempts >= OTP_VERIFY_MAX_FAILED_ATTEMPTS:
            otp.lock_until = now + timedelta(seconds=OTP_VERIFY_LOCK_SECONDS)
        db.commit()
        if otp.failed_attempts >= OTP_VERIFY_MAX_FAILED_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many invalid OTP attempts. Try again later.",
            )
        raise HTTPException(status_code=400, detail="Invalid OTP")

    account: Account
    if payload.role == Role.user:
        user = db.scalar(
            select(User).where(
                and_(User.tenant_id == payload.tenant_id, User.phone == payload.phone)
            )
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        account = db.scalar(
            select(Account).where(
                and_(
                    Account.phone == payload.phone,
                    Account.tenant_id == payload.tenant_id,
                    Account.role == Role.user,
                )
            )
        )
        if not account:
            account = Account(
                tenant_id=payload.tenant_id,
                role=Role.user,
                full_name=f"User {payload.phone}",
                phone=payload.phone,
            )
            db.add(account)
            db.flush()
    else:
        account = db.scalar(
            select(Account).where(
                and_(
                    Account.phone == payload.phone,
                    Account.role == payload.role,
                    Account.tenant_id == payload.tenant_id,
                )
            )
        )
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

    otp.used = True
    otp.failed_attempts = 0
    otp.lock_until = None
    db.commit()
    token = create_access_token(account.account_id, account.role, account.tenant_id)
    return AuthTokenOut(
        access_token=token,
        role=account.role,
        tenant_id=account.tenant_id,
        account_id=account.account_id,
    )
