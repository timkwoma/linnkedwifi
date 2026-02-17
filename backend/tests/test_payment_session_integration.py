from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import and_, select

from linkedwifi_saas.database import SessionLocal
from linkedwifi_saas.main import app
from linkedwifi_saas.models import Package, Payment, PaymentStatus, SessionModel, SessionStatus, Tenant, User


def test_mpesa_callback_creates_session_and_replay_is_idempotent(monkeypatch) -> None:
    tenant_id = None
    user_id = None
    package_id = None
    phone = None
    checkout_id = f"ws-co-{uuid4()}"
    receipt = f"R-{str(uuid4())[:8]}"

    # Avoid FreeRADIUS SQL writes in integration CI DB.
    monkeypatch.setattr("linkedwifi_saas.session_engine.authorize_session", lambda **kwargs: None)

    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.email == "ops@linkedwifi.test"))
        assert tenant is not None
        tenant_id = tenant.tenant_id

        user = db.scalar(select(User).where(and_(User.tenant_id == tenant_id, User.phone == "+254700100001")))
        assert user is not None
        user_id = user.user_id
        phone = user.phone

        package = db.scalar(select(Package).where(Package.tenant_id == tenant_id).limit(1))
        assert package is not None
        package_id = package.package_id
        before_count = len(
            db.scalars(
                select(SessionModel).where(
                    and_(
                        SessionModel.tenant_id == tenant_id,
                        SessionModel.user_id == user_id,
                        SessionModel.package_id == package_id,
                        SessionModel.status == SessionStatus.active,
                    )
                )
            ).all()
        )

        payment = Payment(
            tenant_id=tenant_id,
            user_id=user_id,
            package_id=package_id,
            phone=phone,
            amount=Decimal(str(package.price)),
            status=PaymentStatus.pending,
            mpesa_checkout_request_id=checkout_id,
        )
        db.add(payment)
        db.commit()
        payment_id = payment.payment_id

    client = TestClient(app)
    payload = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": checkout_id,
                "ResultCode": 0,
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "MpesaReceiptNumber", "Value": receipt},
                        {"Name": "ClientMAC", "Value": "AA:BB:CC:DD:EE:FF"},
                        {"Name": "ClientIP", "Value": "10.0.0.10"},
                    ]
                },
            }
        }
    }

    first = client.post("/payments/mpesa/callback", json=payload)
    assert first.status_code == 200
    assert first.json() == {"result": "ok"}

    with SessionLocal() as db:
        payment_after = db.get(Payment, payment_id)
        assert payment_after is not None
        assert payment_after.status == PaymentStatus.success
        assert payment_after.mpesa_receipt == receipt

        sessions = db.scalars(
            select(SessionModel).where(
                and_(
                    SessionModel.tenant_id == tenant_id,
                    SessionModel.user_id == user_id,
                    SessionModel.package_id == package_id,
                    SessionModel.status == SessionStatus.active,
                )
            )
        ).all()
        assert len(sessions) == before_count + 1

    replay = client.post("/payments/mpesa/callback", json=payload)
    assert replay.status_code == 200
    assert replay.json() == {"result": "ignored", "reason": "already_processed"}

    with SessionLocal() as db:
        sessions_after_replay = db.scalars(
            select(SessionModel).where(
                and_(
                    SessionModel.tenant_id == tenant_id,
                    SessionModel.user_id == user_id,
                    SessionModel.package_id == package_id,
                    SessionModel.status == SessionStatus.active,
                )
            )
        ).all()
        assert len(sessions_after_replay) == before_count + 1


def test_mpesa_callback_failure_marks_payment_failed_and_creates_no_session(monkeypatch) -> None:
    tenant_id = None
    user_id = None
    package_id = None
    phone = None
    checkout_id = f"ws-co-{uuid4()}"

    # Ensure no external FreeRADIUS dependency in CI.
    monkeypatch.setattr("linkedwifi_saas.session_engine.authorize_session", lambda **kwargs: None)

    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.email == "ops@linkedwifi.test"))
        assert tenant is not None
        tenant_id = tenant.tenant_id

        user = db.scalar(select(User).where(and_(User.tenant_id == tenant_id, User.phone == "+254700100001")))
        assert user is not None
        user_id = user.user_id
        phone = user.phone

        package = db.scalar(select(Package).where(Package.tenant_id == tenant_id).limit(1))
        assert package is not None
        package_id = package.package_id
        before_count = len(
            db.scalars(
                select(SessionModel).where(
                    and_(
                        SessionModel.tenant_id == tenant_id,
                        SessionModel.user_id == user_id,
                        SessionModel.package_id == package_id,
                        SessionModel.status == SessionStatus.active,
                    )
                )
            ).all()
        )

        payment = Payment(
            tenant_id=tenant_id,
            user_id=user_id,
            package_id=package_id,
            phone=phone,
            amount=Decimal(str(package.price)),
            status=PaymentStatus.pending,
            mpesa_checkout_request_id=checkout_id,
        )
        db.add(payment)
        db.commit()
        payment_id = payment.payment_id

    client = TestClient(app)
    payload = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": checkout_id,
                "ResultCode": 1032,
                "ResultDesc": "Request cancelled by user",
            }
        }
    }

    resp = client.post("/payments/mpesa/callback", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"result": "ok"}

    with SessionLocal() as db:
        payment_after = db.get(Payment, payment_id)
        assert payment_after is not None
        assert payment_after.status == PaymentStatus.failed

        sessions = db.scalars(
            select(SessionModel).where(
                and_(
                    SessionModel.tenant_id == tenant_id,
                    SessionModel.user_id == user_id,
                    SessionModel.package_id == package_id,
                    SessionModel.status == SessionStatus.active,
                )
            )
        ).all()
        assert len(sessions) == before_count
