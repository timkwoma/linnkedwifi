from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .models import PaymentStatus, Role, SessionStatus


class OTPRequestIn(BaseModel):
    phone: str = Field(min_length=10, max_length=20)
    role: Role
    tenant_id: UUID | None = None


class OTPVerifyIn(BaseModel):
    phone: str = Field(min_length=10, max_length=20)
    role: Role
    tenant_id: UUID | None = None
    code: str = Field(min_length=4, max_length=8)


class AuthTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    tenant_id: UUID | None = None
    account_id: UUID


class SessionCreateFromPaymentIn(BaseModel):
    tenant_id: UUID
    user_id: UUID
    package_id: UUID
    phone: str
    mac_address: str | None = None
    ip_address: str | None = None


class SessionReconnectIn(BaseModel):
    tenant_id: UUID
    phone: str
    mac_address: str
    ip_address: str


class SessionOut(BaseModel):
    session_id: UUID
    tenant_id: UUID
    user_id: UUID
    package_id: UUID
    phone: str
    mac_address: str | None
    ip_address: str | None
    start_time: datetime
    end_time: datetime
    status: SessionStatus

    model_config = {"from_attributes": True}


class MpesaSTKPushIn(BaseModel):
    tenant_id: UUID
    phone: str
    package_id: UUID


class PaymentOut(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    amount: float
    mpesa_checkout_request_id: str | None
    mpesa_receipt: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
