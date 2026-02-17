from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from linkedwifi_saas.models import DeviceStatus, Role, TicketStatus
from linkedwifi_saas.routers import devices as devices_router
from linkedwifi_saas.routers import ispadmin as ispadmin_router


def test_update_package_changes_fields_and_price() -> None:
    tenant_id = uuid4()
    package_id = uuid4()
    account = SimpleNamespace(role=Role.isp_admin, tenant_id=tenant_id)
    package = SimpleNamespace(tenant_id=tenant_id, name="Old", price=0)
    db = MagicMock()
    db.scalar.return_value = package

    payload = ispadmin_router.PackageUpdateIn(name="New", price=99.5, active=False)
    result = ispadmin_router.update_package(tenant_id, package_id, payload, db, account)

    assert result == {"message": "updated"}
    assert package.name == "New"
    assert float(package.price) == 99.5
    assert package.active is False
    db.commit.assert_called_once()


def test_delete_package_soft_deactivates() -> None:
    tenant_id = uuid4()
    package_id = uuid4()
    account = SimpleNamespace(role=Role.isp_admin, tenant_id=tenant_id)
    package = SimpleNamespace(tenant_id=tenant_id, active=True)
    db = MagicMock()
    db.scalar.return_value = package

    result = ispadmin_router.delete_package(tenant_id, package_id, db, account)

    assert result == {"message": "deactivated"}
    assert package.active is False
    db.commit.assert_called_once()


def test_update_ticket_status_sets_resolved_at() -> None:
    tenant_id = uuid4()
    ticket_id = uuid4()
    account = SimpleNamespace(role=Role.isp_admin, tenant_id=tenant_id)
    ticket = SimpleNamespace(tenant_id=tenant_id, status=TicketStatus.open, resolved_at=None)
    db = MagicMock()
    db.scalar.return_value = ticket

    payload = ispadmin_router.TicketStatusIn(status=TicketStatus.resolved)
    result = ispadmin_router.update_ticket_status(tenant_id, ticket_id, payload, db, account)

    assert result == {"message": "updated"}
    assert ticket.status == TicketStatus.resolved
    assert ticket.resolved_at is not None
    db.commit.assert_called_once()


def test_update_device_conflicting_mac_rejected() -> None:
    tenant_id = uuid4()
    device_id = uuid4()
    account = SimpleNamespace(role=Role.isp_admin, tenant_id=tenant_id)
    device = SimpleNamespace(
        tenant_id=tenant_id,
        device_id=device_id,
        mac="AA:AA:AA:AA:AA:01",
        status=DeviceStatus.offline,
    )
    db = MagicMock()
    db.get.return_value = device
    db.scalar.return_value = SimpleNamespace(device_id=uuid4())

    payload = devices_router.DeviceUpdateIn(mac="AA:AA:AA:AA:AA:99")
    with pytest.raises(HTTPException) as exc:
        devices_router.update_device(device_id, payload, db, account)

    assert exc.value.status_code == 409


def test_delete_device_removes_record() -> None:
    tenant_id = uuid4()
    device_id = uuid4()
    account = SimpleNamespace(role=Role.isp_admin, tenant_id=tenant_id)
    device = SimpleNamespace(tenant_id=tenant_id, device_id=device_id)
    db = MagicMock()
    db.get.return_value = device

    result = devices_router.delete_device(device_id, db, account)

    assert result == {"message": "deleted"}
    db.delete.assert_called_once_with(device)
    db.commit.assert_called_once()
