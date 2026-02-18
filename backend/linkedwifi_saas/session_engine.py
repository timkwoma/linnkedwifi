from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from .models import Package, SessionModel, SessionStatus, User
from .utils.freeradius import authorize_session, block_session


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_session_after_payment(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID,
    package_id: UUID,
    phone: str,
    mac_address: str | None,
    ip_address: str | None,
) -> SessionModel:
    user = db.scalar(
        select(User).where(and_(User.user_id == user_id, User.tenant_id == tenant_id))
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    package = db.scalar(
        select(Package).where(
            and_(Package.package_id == package_id, Package.tenant_id == tenant_id)
        )
    )
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    now = _now_utc()
    end_time = now + timedelta(minutes=package.duration_minutes)
    session = SessionModel(
        tenant_id=tenant_id,
        user_id=user_id,
        package_id=package_id,
        phone=phone,
        mac_address=mac_address,
        ip_address=ip_address,
        start_time=now,
        end_time=end_time,
        status=SessionStatus.active,
    )
    db.add(session)

    user.mac_address = mac_address
    user.ip_address = ip_address
    db.flush()

    authorize_session(
        phone=phone, mac_address=mac_address, ip_address=ip_address, expires_at=end_time
    )
    return session


def reconnect_session(
    db: Session,
    *,
    tenant_id: UUID,
    phone: str,
    mac_address: str,
    ip_address: str,
) -> SessionModel:
    now = _now_utc()
    session = db.scalar(
        select(SessionModel)
        .where(
            and_(
                SessionModel.tenant_id == tenant_id,
                SessionModel.phone == phone,
                SessionModel.status == SessionStatus.active,
            )
        )
        .order_by(SessionModel.end_time.desc())
    )
    if not session:
        raise HTTPException(status_code=404, detail="No active session found")

    if session.end_time.tzinfo is None:
        end = session.end_time.replace(tzinfo=timezone.utc)
    else:
        end = session.end_time
    if end <= now:
        session.status = SessionStatus.expired
        block_session(phone)
        db.flush()
        raise HTTPException(status_code=403, detail="Session expired")

    session.mac_address = mac_address
    session.ip_address = ip_address
    session.last_reconnected_at = now
    authorize_session(
        phone=phone, mac_address=mac_address, ip_address=ip_address, expires_at=end
    )
    return session


def expire_stale_sessions(db: Session) -> int:
    now = _now_utc()
    stale = db.scalars(
        select(SessionModel).where(
            and_(
                SessionModel.status == SessionStatus.active,
                SessionModel.end_time <= now,
            )
        )
    ).all()

    for session in stale:
        session.status = SessionStatus.expired
        block_session(session.phone)

    return len(stale)
