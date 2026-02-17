from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Account, Payment, PaymentStatus, Role, SessionModel, SessionStatus, Tenant
from ..security import require_role

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


class TenantCreateIn(BaseModel):
    name: str
    email: EmailStr
    plan: str = "starter"
    admin_name: str
    admin_phone: str
    admin_email: EmailStr | None = None


@router.get("/stats")
def stats(
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.super_admin)),
) -> dict:
    return {
        "tenants": db.scalar(select(func.count(Tenant.tenant_id))) or 0,
        "accounts": db.scalar(select(func.count(Account.account_id))) or 0,
        "payments_success": db.scalar(
            select(func.count(Payment.payment_id)).where(Payment.status == PaymentStatus.success)
        )
        or 0,
        "active_sessions": db.scalar(
            select(func.count(SessionModel.session_id)).where(SessionModel.status == SessionStatus.active)
        )
        or 0,
    }


@router.get("/tenants")
def list_tenants(
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.super_admin)),
) -> list[dict]:
    rows = db.scalars(select(Tenant).order_by(Tenant.created_at.desc())).all()
    return [
        {
            "tenant_id": t.tenant_id,
            "name": t.name,
            "email": t.email,
            "plan": t.plan,
            "active": t.active,
            "created_at": t.created_at,
        }
        for t in rows
    ]


@router.post("/tenants")
def create_tenant(
    payload: TenantCreateIn,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.super_admin)),
) -> dict:
    exists = db.scalar(select(Tenant).where(Tenant.email == payload.email))
    if exists:
        raise HTTPException(status_code=409, detail="Tenant email exists")
    tenant = Tenant(name=payload.name, email=str(payload.email), plan=payload.plan)
    db.add(tenant)
    db.flush()
    admin = Account(
        tenant_id=tenant.tenant_id,
        role=Role.isp_admin,
        full_name=payload.admin_name,
        phone=payload.admin_phone,
        email=str(payload.admin_email) if payload.admin_email else None,
    )
    db.add(admin)
    db.commit()
    return {"tenant_id": tenant.tenant_id, "isp_admin_account_id": admin.account_id}


@router.delete("/tenants/{tenant_id}")
def deactivate_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.super_admin)),
) -> dict:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.active = False
    db.commit()
    return {"message": "Tenant deactivated"}
