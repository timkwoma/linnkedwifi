from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Device, DeviceStatus, Role
from ..security import enforce_tenant_access, require_role

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceCreateIn(BaseModel):
    tenant_id: UUID
    device_type: str = "mikrotik"
    name: str
    ip: str
    mac: str


class DeviceStatusIn(BaseModel):
    status: DeviceStatus


class DeviceUpdateIn(BaseModel):
    device_type: str | None = None
    name: str | None = None
    ip: str | None = None
    mac: str | None = None
    status: DeviceStatus | None = None


@router.get("")
def list_devices(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> list[dict]:
    enforce_tenant_access(account, tenant_id)
    rows = db.scalars(select(Device).where(Device.tenant_id == tenant_id)).all()
    return [
        {
            "device_id": d.device_id,
            "tenant_id": d.tenant_id,
            "device_type": d.device_type,
            "name": d.name,
            "ip": d.ip,
            "mac": d.mac,
            "status": d.status,
            "last_seen": d.last_seen,
        }
        for d in rows
    ]


@router.post("")
def create_device(
    payload: DeviceCreateIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    enforce_tenant_access(account, payload.tenant_id)
    exists = db.scalar(
        select(Device).where(
            and_(Device.tenant_id == payload.tenant_id, Device.mac == payload.mac)
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail="Device MAC already exists")
    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return {"device_id": device.device_id}


@router.patch("/{device_id}/status")
def update_device_status(
    device_id: UUID,
    payload: DeviceStatusIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    enforce_tenant_access(account, device.tenant_id)
    device.status = payload.status
    device.last_seen = datetime.now(timezone.utc)
    db.commit()
    return {"message": "updated"}


@router.patch("/{device_id}")
def update_device(
    device_id: UUID,
    payload: DeviceUpdateIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    enforce_tenant_access(account, device.tenant_id)

    data = payload.model_dump(exclude_unset=True)
    if "mac" in data:
        duplicate = db.scalar(
            select(Device).where(
                and_(
                    Device.tenant_id == device.tenant_id,
                    Device.mac == data["mac"],
                    Device.device_id != device_id,
                )
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Device MAC already exists")

    for field, value in data.items():
        setattr(device, field, value)
    device.last_seen = datetime.now(timezone.utc)
    db.commit()
    return {"message": "updated"}


@router.delete("/{device_id}")
def delete_device(
    device_id: UUID,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.isp_admin, Role.super_admin)),
) -> dict:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    enforce_tenant_access(account, device.tenant_id)
    db.delete(device)
    db.commit()
    return {"message": "deleted"}
