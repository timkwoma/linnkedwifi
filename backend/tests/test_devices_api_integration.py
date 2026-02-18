from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from linkedwifi_saas.database import SessionLocal
from linkedwifi_saas.main import app
from linkedwifi_saas.models import Device, OTPCode, Tenant


def _login_isp_admin(client: TestClient) -> tuple[str, str]:
    phone = "+254700000002"
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.email == "ops@linkedwifi.test"))
        assert tenant is not None
        tenant_id = str(tenant.tenant_id)
        db.execute(
            delete(OTPCode).where(
                OTPCode.phone == phone, OTPCode.tenant_id == tenant.tenant_id
            )
        )
        db.commit()

    req = client.post(
        "/auth/request-otp",
        json={"phone": phone, "role": "isp_admin", "tenant_id": tenant_id},
    )
    assert req.status_code == 200
    code = req.json()["dev_otp"]
    ver = client.post(
        "/auth/verify-otp",
        json={
            "phone": phone,
            "role": "isp_admin",
            "tenant_id": tenant_id,
            "code": code,
        },
    )
    assert ver.status_code == 200
    return ver.json()["access_token"], tenant_id


def test_device_create_update_delete_integration() -> None:
    client = TestClient(app)
    token, tenant_id = _login_isp_admin(client)

    device_name = f"Integration Device {uuid4().hex[:8]}"
    device_mac = f"AA:EE:{uuid4().hex[:2]}:{uuid4().hex[:2]}:{uuid4().hex[:2]}:{uuid4().hex[:2]}".upper()
    create_resp = client.post(
        "/devices",
        json={
            "tenant_id": tenant_id,
            "device_type": "mikrotik",
            "name": device_name,
            "ip": "10.5.99.10",
            "mac": device_mac,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    device_id = create_resp.json()["device_id"]

    list_resp = client.get(
        f"/devices?tenant_id={tenant_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    assert any(d["device_id"] == device_id for d in list_resp.json())

    patch_resp = client.patch(
        f"/devices/{device_id}",
        json={"name": f"{device_name} Updated", "status": "online"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json() == {"message": "updated"}

    status_resp = client.patch(
        f"/devices/{device_id}/status",
        json={"status": "maintenance"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json() == {"message": "updated"}

    delete_resp = client.delete(
        f"/devices/{device_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"message": "deleted"}

    with SessionLocal() as db:
        removed = db.get(Device, device_id)
        assert removed is None
