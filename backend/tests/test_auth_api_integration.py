from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from linkedwifi_saas.database import SessionLocal
from linkedwifi_saas.main import app
from linkedwifi_saas.models import OTPCode, Tenant


def test_isp_admin_otp_login_flow_against_real_db() -> None:
    phone = "+254700000002"

    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.email == "ops@linkedwifi.test"))
        assert tenant is not None
        db.execute(
            delete(OTPCode).where(
                OTPCode.phone == phone, OTPCode.tenant_id == tenant.tenant_id
            )
        )
        db.commit()
        tenant_id = str(tenant.tenant_id)

    client = TestClient(app)
    request_payload = {
        "phone": phone,
        "role": "isp_admin",
        "tenant_id": tenant_id,
    }
    request_resp = client.post("/auth/request-otp", json=request_payload)
    assert request_resp.status_code == 200
    request_data = request_resp.json()
    assert request_data["message"] == "OTP generated"
    otp_code = request_data["dev_otp"]
    assert isinstance(otp_code, str) and len(otp_code) == 6

    verify_payload = {
        "phone": phone,
        "role": "isp_admin",
        "tenant_id": tenant_id,
        "code": otp_code,
    }
    verify_resp = client.post("/auth/verify-otp", json=verify_payload)
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["role"] == "isp_admin"
    assert verify_data["tenant_id"] == tenant_id
    assert verify_data["access_token"]
