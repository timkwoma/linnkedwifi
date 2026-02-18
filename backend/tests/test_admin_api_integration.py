from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from linkedwifi_saas.database import SessionLocal
from linkedwifi_saas.main import app
from linkedwifi_saas.models import Package, Tenant, Ticket, User


def _otp_login(
    client: TestClient, *, phone: str, role: str, tenant_id: str | None
) -> str:
    req = client.post(
        "/auth/request-otp",
        json={"phone": phone, "role": role, "tenant_id": tenant_id},
    )
    assert req.status_code == 200
    code = req.json()["dev_otp"]
    ver = client.post(
        "/auth/verify-otp",
        json={"phone": phone, "role": role, "tenant_id": tenant_id, "code": code},
    )
    assert ver.status_code == 200
    return ver.json()["access_token"]


def test_superadmin_create_and_deactivate_tenant_integration() -> None:
    client = TestClient(app)
    super_token = _otp_login(
        client,
        phone="+254700000001",
        role="super_admin",
        tenant_id=None,
    )

    tenant_email = f"tenant-{uuid4().hex[:8]}@example.com"
    create_resp = client.post(
        "/superadmin/tenants",
        json={
            "name": "Integration Tenant",
            "email": tenant_email,
            "plan": "starter",
            "admin_name": "Integration Admin",
            "admin_phone": f"+2547{uuid4().int % 10_000_000:07d}",
            "admin_email": f"admin-{uuid4().hex[:6]}@example.com",
        },
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert create_resp.status_code == 200
    created_tenant_id = create_resp.json()["tenant_id"]

    deactivate_resp = client.delete(
        f"/superadmin/tenants/{created_tenant_id}",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json() == {"message": "Tenant deactivated"}

    with SessionLocal() as db:
        tenant = db.get(Tenant, created_tenant_id)
        assert tenant is not None
        assert tenant.active is False


def test_ispadmin_package_and_ticket_workflow_integration() -> None:
    client = TestClient(app)
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.email == "ops@linkedwifi.test"))
        user = db.scalar(select(User).where(User.phone == "+254700100001"))
        assert tenant is not None
        assert user is not None
        tenant_id = str(tenant.tenant_id)
        user_id = str(user.user_id)

    isp_token = _otp_login(
        client,
        phone="+254700000002",
        role="isp_admin",
        tenant_id=tenant_id,
    )

    pkg_name = f"Integration Package {uuid4().hex[:8]}"
    create_pkg = client.post(
        f"/ispadmin/packages?tenant_id={tenant_id}",
        json={
            "name": pkg_name,
            "duration_minutes": 45,
            "speed_limit_rx": 6000,
            "speed_limit_tx": 2500,
            "price": 33.0,
            "category": "hotspot",
        },
        headers={"Authorization": f"Bearer {isp_token}"},
    )
    assert create_pkg.status_code == 200
    package_id = create_pkg.json()["package_id"]

    patch_pkg = client.patch(
        f"/ispadmin/packages/{package_id}?tenant_id={tenant_id}",
        json={"price": 44.0, "active": True},
        headers={"Authorization": f"Bearer {isp_token}"},
    )
    assert patch_pkg.status_code == 200
    assert patch_pkg.json() == {"message": "updated"}

    delete_pkg = client.delete(
        f"/ispadmin/packages/{package_id}?tenant_id={tenant_id}",
        headers={"Authorization": f"Bearer {isp_token}"},
    )
    assert delete_pkg.status_code == 200
    assert delete_pkg.json() == {"message": "deactivated"}

    create_ticket = client.post(
        f"/ispadmin/tickets?tenant_id={tenant_id}",
        json={"user_id": user_id, "subject": "Integration ticket"},
        headers={"Authorization": f"Bearer {isp_token}"},
    )
    assert create_ticket.status_code == 200
    ticket_id = create_ticket.json()["ticket_id"]

    resolve_ticket = client.patch(
        f"/ispadmin/tickets/{ticket_id}/status?tenant_id={tenant_id}",
        json={"status": "resolved"},
        headers={"Authorization": f"Bearer {isp_token}"},
    )
    assert resolve_ticket.status_code == 200
    assert resolve_ticket.json() == {"message": "updated"}

    with SessionLocal() as db:
        package = db.get(Package, package_id)
        assert package is not None
        assert float(package.price) == 44.0
        assert package.active is False

        ticket = db.get(Ticket, ticket_id)
        assert ticket is not None
        status_value = (
            ticket.status.value
            if hasattr(ticket.status, "value")
            else str(ticket.status)
        )
        assert status_value == "resolved"
        assert ticket.resolved_at is not None
