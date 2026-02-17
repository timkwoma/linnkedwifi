from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..database import get_db, settings
from ..models import Package, Payment, PaymentStatus, Role, User
from ..schemas import MpesaSTKPushIn, PaymentOut
from ..security import enforce_tenant_access, require_role
from ..session_engine import create_session_after_payment
from ..utils.mpesa import stk_push

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/mpesa/stk-push", response_model=PaymentOut)
async def initiate_stk_push(
    payload: MpesaSTKPushIn,
    db: Session = Depends(get_db),
    account=Depends(require_role(Role.user, Role.isp_admin, Role.super_admin)),
) -> PaymentOut:
    enforce_tenant_access(account, payload.tenant_id)
    if account.role == Role.user and account.phone != payload.phone:
        raise HTTPException(status_code=403, detail="Phone access denied")
    package = db.scalar(
        select(Package).where(
            and_(Package.package_id == payload.package_id, Package.tenant_id == payload.tenant_id)
        )
    )
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    user = db.scalar(
        select(User).where(and_(User.tenant_id == payload.tenant_id, User.phone == payload.phone))
    )
    if not user:
        user = User(tenant_id=payload.tenant_id, phone=payload.phone, status="active")
        db.add(user)
        db.flush()

    response = await stk_push(
        phone=payload.phone,
        amount=float(package.price),
        account_reference=f"LINKEDWIFI-{payload.tenant_id}",
        transaction_desc=f"Package {package.name}",
    )

    payment = Payment(
        tenant_id=payload.tenant_id,
        user_id=user.user_id,
        package_id=package.package_id,
        phone=payload.phone,
        amount=Decimal(str(package.price)),
        status=PaymentStatus.pending,
        mpesa_checkout_request_id=response.get("CheckoutRequestID"),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return PaymentOut.model_validate(payment)


@router.post("/mpesa/callback")
def mpesa_callback(
    payload: dict,
    db: Session = Depends(get_db),
    callback_secret: str | None = Header(default=None, alias="X-Callback-Secret"),
) -> dict:
    if settings.mpesa_callback_secret and callback_secret != settings.mpesa_callback_secret:
        raise HTTPException(status_code=403, detail="Invalid callback signature")

    stk = payload.get("Body", {}).get("stkCallback", {})
    checkout_request_id = stk.get("CheckoutRequestID")
    raw_result_code = stk.get("ResultCode")
    if checkout_request_id is None or raw_result_code is None:
        raise HTTPException(status_code=400, detail="Invalid callback payload")
    try:
        result_code = int(raw_result_code)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid callback payload") from None

    payment = db.scalar(
        select(Payment).where(Payment.mpesa_checkout_request_id == checkout_request_id)
    )
    if not payment:
        return {"message": "Payment not mapped"}

    if payment.status != PaymentStatus.pending:
        return {"result": "ignored", "reason": "already_processed"}

    if result_code == 0:
        items = stk.get("CallbackMetadata", {}).get("Item", [])
        metadata = {item.get("Name"): item.get("Value") for item in items}
        payment.status = PaymentStatus.success
        payment.mpesa_receipt = metadata.get("MpesaReceiptNumber")
        create_session_after_payment(
            db,
            tenant_id=payment.tenant_id,
            user_id=payment.user_id,
            package_id=payment.package_id,
            phone=payment.phone,
            mac_address=metadata.get("ClientMAC"),
            ip_address=metadata.get("ClientIP"),
        )
    else:
        payment.status = PaymentStatus.failed

    db.commit()
    return {"result": "ok"}
