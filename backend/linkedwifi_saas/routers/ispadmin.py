from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Message,
    Package,
    PackageCategory,
    Payment,
    PaymentStatus,
    Role,
    SessionModel,
    SessionStatus,
    Ticket,
    TicketStatus,
    User,
)
from ..security import enforce_tenant_access, get_current_account, require_role

router = APIRouter(prefix="/ispadmin", tags=["ispadmin"])


class PackageIn(BaseModel):
    name: str
    duration_minutes: int
    speed_limit_rx: int
    speed_limit_tx: int
    price: float
    category: PackageCategory = PackageCategory.hotspot


class PackageUpdateIn(BaseModel):
    name: str | None = None
    duration_minutes: int | None = None
    speed_limit_rx: int | None = None
    speed_limit_tx: int | None = None
    price: float | None = None
    category: PackageCategory | None = None
    active: bool | None = None


class TicketIn(BaseModel):
    user_id: UUID
    subject: str


class TicketStatusIn(BaseModel):
    status: TicketStatus


class MessageIn(BaseModel):
    sender: str
    receiver: str
    type: str = "notification"
    content: str


@router.get("/stats")
def tenant_stats(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enforce_tenant_access(account, tenant_id)
    return {
        "users": db.scalar(select(func.count(User.user_id)).where(User.tenant_id == tenant_id)) or 0,
        "packages": db.scalar(
            select(func.count(Package.package_id)).where(Package.tenant_id == tenant_id)
        )
        or 0,
        "payments_total": float(
            db.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    and_(Payment.tenant_id == tenant_id, Payment.status == PaymentStatus.success)
                )
            )
            or 0
        ),
        "active_sessions": db.scalar(
            select(func.count(SessionModel.session_id)).where(
                and_(SessionModel.tenant_id == tenant_id, SessionModel.status == SessionStatus.active)
            )
        )
        or 0,
        "open_tickets": db.scalar(
            select(func.count(Ticket.ticket_id)).where(
                and_(Ticket.tenant_id == tenant_id, Ticket.status != TicketStatus.resolved)
            )
        )
        or 0,
    }


@router.get("/users")
def list_users(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> list[dict]:
    enforce_tenant_access(account, tenant_id)
    users = db.scalars(select(User).where(User.tenant_id == tenant_id)).all()
    return [
        {
            "user_id": u.user_id,
            "phone": u.phone,
            "mac_address": u.mac_address,
            "ip_address": u.ip_address,
            "status": u.status,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.get("/packages")
def list_packages(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> list[dict]:
    enforce_tenant_access(account, tenant_id)
    items = db.scalars(select(Package).where(Package.tenant_id == tenant_id)).all()
    return [
        {
            "package_id": p.package_id,
            "name": p.name,
            "duration_minutes": p.duration_minutes,
            "speed_limit_rx": p.speed_limit_rx,
            "speed_limit_tx": p.speed_limit_tx,
            "price": float(p.price),
            "category": p.category,
            "active": p.active,
        }
        for p in items
    ]


@router.post("/packages")
def create_package(
    tenant_id: UUID,
    payload: PackageIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enforce_tenant_access(account, tenant_id)
    p = Package(
        tenant_id=tenant_id,
        name=payload.name,
        duration_minutes=payload.duration_minutes,
        speed_limit_rx=payload.speed_limit_rx,
        speed_limit_tx=payload.speed_limit_tx,
        price=Decimal(str(payload.price)),
        category=payload.category,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"package_id": p.package_id}


@router.patch("/packages/{package_id}")
def update_package(
    tenant_id: UUID,
    package_id: UUID,
    payload: PackageUpdateIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enforce_tenant_access(account, tenant_id)
    p = db.scalar(
        select(Package).where(and_(Package.package_id == package_id, Package.tenant_id == tenant_id))
    )
    if not p:
        raise HTTPException(status_code=404, detail="Package not found")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "price" and value is not None:
            setattr(p, field, Decimal(str(value)))
        else:
            setattr(p, field, value)

    db.commit()
    return {"message": "updated"}


@router.delete("/packages/{package_id}")
def delete_package(
    tenant_id: UUID,
    package_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enforce_tenant_access(account, tenant_id)
    p = db.scalar(
        select(Package).where(and_(Package.package_id == package_id, Package.tenant_id == tenant_id))
    )
    if not p:
        raise HTTPException(status_code=404, detail="Package not found")

    # Soft-delete to preserve historical payment/session integrity.
    p.active = False
    db.commit()
    return {"message": "deactivated"}


@router.get("/payments")
def list_payments(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> list[dict]:
    enforce_tenant_access(account, tenant_id)
    rows = db.scalars(
        select(Payment).where(Payment.tenant_id == tenant_id).order_by(Payment.created_at.desc())
    ).all()
    return [
        {
            "payment_id": p.payment_id,
            "phone": p.phone,
            "amount": float(p.amount),
            "status": p.status,
            "receipt": p.mpesa_receipt,
            "created_at": p.created_at,
        }
        for p in rows
    ]


@router.get("/tickets")
def list_tickets(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> list[dict]:
    enforce_tenant_access(account, tenant_id)
    rows = db.scalars(select(Ticket).where(Ticket.tenant_id == tenant_id)).all()
    return [
        {
            "ticket_id": t.ticket_id,
            "user_id": t.user_id,
            "subject": t.subject,
            "status": t.status,
            "created_at": t.created_at,
            "resolved_at": t.resolved_at,
        }
        for t in rows
    ]


@router.post("/tickets")
def create_ticket(
    tenant_id: UUID,
    payload: TicketIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enforce_tenant_access(account, tenant_id)
    user = db.scalar(
        select(User).where(and_(User.tenant_id == tenant_id, User.user_id == payload.user_id))
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    t = Ticket(tenant_id=tenant_id, user_id=payload.user_id, subject=payload.subject)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"ticket_id": t.ticket_id}


@router.patch("/tickets/{ticket_id}/status")
def update_ticket_status(
    tenant_id: UUID,
    ticket_id: UUID,
    payload: TicketStatusIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enforce_tenant_access(account, tenant_id)
    t = db.scalar(select(Ticket).where(and_(Ticket.ticket_id == ticket_id, Ticket.tenant_id == tenant_id)))
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    t.status = payload.status
    if payload.status == TicketStatus.resolved:
        t.resolved_at = datetime.now(timezone.utc)
    else:
        t.resolved_at = None
    db.commit()
    return {"message": "updated"}


@router.get("/messages")
def list_messages(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> list[dict]:
    enforce_tenant_access(account, tenant_id)
    rows = db.scalars(select(Message).where(Message.tenant_id == tenant_id)).all()
    return [
        {
            "message_id": m.message_id,
            "sender": m.sender,
            "receiver": m.receiver,
            "type": m.type,
            "content": m.content,
            "timestamp": m.timestamp,
        }
        for m in rows
    ]


@router.post("/messages")
def create_message(
    tenant_id: UUID,
    payload: MessageIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enforce_tenant_access(account, tenant_id)
    m = Message(tenant_id=tenant_id, **payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"message_id": m.message_id}


@router.get("/me")
def me(account=Depends(get_current_account)) -> dict:
    return {
        "account_id": account.account_id,
        "tenant_id": account.tenant_id,
        "role": account.role,
        "phone": account.phone,
        "full_name": account.full_name,
    }
