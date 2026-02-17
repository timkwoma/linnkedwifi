from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, SessionModel, SessionStatus
from ..schemas import SessionCreateFromPaymentIn, SessionOut, SessionReconnectIn
from ..security import enforce_tenant_access, require_role
from ..session_engine import create_session_after_payment, reconnect_session
from ..tasks import enqueue_cleanup_job, run_worker_once

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/activate", response_model=SessionOut)
def activate_session(
    payload: SessionCreateFromPaymentIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.user, Role.isp_admin, Role.super_admin)),
) -> SessionOut:
    enforce_tenant_access(account, payload.tenant_id)
    if account.role == Role.user and account.phone != payload.phone:
        raise HTTPException(status_code=403, detail="Phone access denied")
    session = create_session_after_payment(
        db,
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        package_id=payload.package_id,
        phone=payload.phone,
        mac_address=payload.mac_address,
        ip_address=payload.ip_address,
    )
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.post("/reconnect", response_model=SessionOut)
def reconnect(
    payload: SessionReconnectIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.user, Role.isp_admin, Role.super_admin)),
) -> SessionOut:
    enforce_tenant_access(account, payload.tenant_id)
    if account.role == Role.user and account.phone != payload.phone:
        raise HTTPException(status_code=403, detail="Phone access denied")
    try:
        session = reconnect_session(
            db,
            tenant_id=payload.tenant_id,
            phone=payload.phone,
            mac_address=payload.mac_address,
            ip_address=payload.ip_address,
        )
    except HTTPException as exc:
        # Persist status transition when an active session is found expired during reconnect.
        if exc.status_code == 403 and str(exc.detail) == "Session expired":
            db.commit()
        raise
    db.commit()
    db.refresh(session)
    return SessionOut.model_validate(session)


@router.get("/active", response_model=SessionOut | None)
def get_active_session(
    tenant_id: UUID,
    phone: str,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.user, Role.isp_admin, Role.super_admin)),
) -> SessionOut | None:
    enforce_tenant_access(account, tenant_id)
    if account.role == Role.user and account.phone != phone:
        raise HTTPException(status_code=403, detail="Phone access denied")
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
        return None
    return SessionOut.model_validate(session)


@router.post("/jobs/enqueue-expiry")
def enqueue_expiry_job(
    _=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enqueue_cleanup_job()
    return {"message": "Session expiry job queued"}


@router.post("/jobs/run-once")
def run_job_once(
    _=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    count = run_worker_once()
    return {"expired_sessions": count}
