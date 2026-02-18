from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import and_, delete, select

from linkedwifi_saas.database import SessionLocal
from linkedwifi_saas.main import app
from linkedwifi_saas.models import (
    OTPCode,
    Package,
    SessionModel,
    SessionStatus,
    Tenant,
    User,
)
from linkedwifi_saas.session_engine import expire_stale_sessions


def _get_isp_admin_token_and_tenant_id(client: TestClient) -> tuple[str, str]:
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

    req = client.post(
        "/auth/request-otp",
        json={"phone": phone, "role": "isp_admin", "tenant_id": tenant_id},
    )
    assert req.status_code == 200
    otp_code = req.json()["dev_otp"]
    ver = client.post(
        "/auth/verify-otp",
        json={
            "phone": phone,
            "role": "isp_admin",
            "tenant_id": tenant_id,
            "code": otp_code,
        },
    )
    assert ver.status_code == 200
    return ver.json()["access_token"], tenant_id


def _get_seeded_user_and_package_ids(tenant_id: str) -> tuple[str, str, str]:
    tenant_uuid = UUID(tenant_id)
    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                and_(User.tenant_id == tenant_uuid, User.phone == "+254700100001")
            )
        )
        package = db.scalar(
            select(Package).where(Package.tenant_id == tenant_uuid).limit(1)
        )
        assert user is not None
        assert package is not None
        return str(user.user_id), str(package.package_id), user.phone


def test_session_reconnect_updates_mac_and_ip(monkeypatch) -> None:
    monkeypatch.setattr(
        "linkedwifi_saas.session_engine.authorize_session", lambda **kwargs: None
    )
    client = TestClient(app)
    token, tenant_id = _get_isp_admin_token_and_tenant_id(client)
    user_id, package_id, phone = _get_seeded_user_and_package_ids(tenant_id)

    create_resp = client.post(
        "/sessions/activate",
        json={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "package_id": package_id,
            "phone": phone,
            "mac_address": "AA:BB:CC:DD:EE:01",
            "ip_address": "10.0.0.10",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200

    reconnect_resp = client.post(
        "/sessions/reconnect",
        json={
            "tenant_id": tenant_id,
            "phone": phone,
            "mac_address": "AA:BB:CC:DD:EE:99",
            "ip_address": "10.0.0.99",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reconnect_resp.status_code == 200
    data = reconnect_resp.json()
    assert data["status"] == "active"
    assert data["mac_address"] == "AA:BB:CC:DD:EE:99"
    assert data["ip_address"] == "10.0.0.99"


def test_expired_session_reconnect_denied_and_cleanup_expires_stale(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "linkedwifi_saas.session_engine.authorize_session", lambda **kwargs: None
    )
    monkeypatch.setattr(
        "linkedwifi_saas.session_engine.block_session", lambda *_args, **_kwargs: None
    )

    client = TestClient(app)
    token, tenant_id = _get_isp_admin_token_and_tenant_id(client)
    tenant_uuid = UUID(tenant_id)
    with SessionLocal() as db:
        package = db.scalar(
            select(Package).where(Package.tenant_id == tenant_uuid).limit(1)
        )
        assert package is not None
        package_id = str(package.package_id)

        phone = f"+25479{uuid4().int % 10_000_000:07d}"
        user = User(
            tenant_id=tenant_uuid,
            phone=phone,
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = str(user.user_id)

    create_resp = client.post(
        "/sessions/activate",
        json={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "package_id": package_id,
            "phone": phone,
            "mac_address": "AA:BB:CC:DD:EE:02",
            "ip_address": "10.0.0.20",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 200
    session_id = create_resp.json()["session_id"]

    with SessionLocal() as db:
        session = db.get(SessionModel, session_id)
        assert session is not None
        session.end_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    reconnect_resp = client.post(
        "/sessions/reconnect",
        json={
            "tenant_id": tenant_id,
            "phone": phone,
            "mac_address": "AA:BB:CC:DD:EE:77",
            "ip_address": "10.0.0.77",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reconnect_resp.status_code == 403
    assert "Session expired" in reconnect_resp.text

    with SessionLocal() as db:
        tenant_uuid = UUID(tenant_id)
        user_uuid = UUID(user_id)
        package_uuid = UUID(package_id)
        session = db.get(SessionModel, session_id)
        assert session is not None
        assert session.status == SessionStatus.expired

        stale = SessionModel(
            tenant_id=tenant_uuid,
            user_id=user_uuid,
            package_id=package_uuid,
            phone=phone,
            mac_address="AA:BB:CC:DD:EE:03",
            ip_address="10.0.0.30",
            start_time=datetime.now(timezone.utc) - timedelta(hours=2),
            end_time=datetime.now(timezone.utc) - timedelta(hours=1),
            status=SessionStatus.active,
        )
        db.add(stale)
        db.commit()

        expired_count = expire_stale_sessions(db)
        db.commit()
        assert expired_count >= 1

        refreshed = db.get(SessionModel, stale.session_id)
        assert refreshed is not None
        assert refreshed.status == SessionStatus.expired
