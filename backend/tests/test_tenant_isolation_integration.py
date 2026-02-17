from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from linkedwifi_saas.database import SessionLocal
from linkedwifi_saas.main import app
from linkedwifi_saas.models import OTPCode, Tenant


def test_isp_admin_cannot_access_other_tenant_stats() -> None:
    phone = "+254700000002"

    with SessionLocal() as db:
        tenant_a = db.scalar(select(Tenant).where(Tenant.email == "ops@linkedwifi.test"))
        tenant_b = db.scalar(select(Tenant).where(Tenant.email == "admin@metronet.test"))
        assert tenant_a is not None
        assert tenant_b is not None
        tenant_a_id = str(tenant_a.tenant_id)
        tenant_b_id = str(tenant_b.tenant_id)
        db.execute(delete(OTPCode).where(OTPCode.phone == phone, OTPCode.tenant_id == tenant_a.tenant_id))
        db.commit()

    client = TestClient(app)
    request_resp = client.post(
        "/auth/request-otp",
        json={
            "phone": phone,
            "role": "isp_admin",
            "tenant_id": tenant_a_id,
        },
    )
    assert request_resp.status_code == 200
    otp_code = request_resp.json()["dev_otp"]

    verify_resp = client.post(
        "/auth/verify-otp",
        json={
            "phone": phone,
            "role": "isp_admin",
            "tenant_id": tenant_a_id,
            "code": otp_code,
        },
    )
    assert verify_resp.status_code == 200
    token = verify_resp.json()["access_token"]

    stats_resp = client.get(
        f"/ispadmin/stats?tenant_id={tenant_b_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stats_resp.status_code == 403
    assert "Tenant access denied" in stats_resp.text
