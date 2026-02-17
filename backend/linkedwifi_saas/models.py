from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Role(str, enum.Enum):
    super_admin = "super_admin"
    isp_admin = "isp_admin"
    user = "user"


class SessionStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    expired = "expired"
    blocked = "blocked"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class DeviceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"


class PackageCategory(str, enum.Enum):
    hotspot = "hotspot"
    home = "home"


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(64), nullable=False, default="starter")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=True, index=True
    )
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_accounts_phone_tenant"),)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(32), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessions: Mapped[list[SessionModel]] = relationship(back_populates="user")
    payments: Mapped[list[Payment]] = relationship(back_populates="user")

    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_users_phone_tenant"),)


class Package(Base):
    __tablename__ = "packages"

    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    speed_limit_rx: Mapped[int] = mapped_column(Integer, nullable=False)
    speed_limit_tx: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[PackageCategory] = mapped_column(
        Enum(PackageCategory), nullable=False, default=PackageCategory.hotspot
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sessions: Mapped[list[SessionModel]] = relationship(back_populates="package")
    payments: Mapped[list[Payment]] = relationship(back_populates="package")

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_package_name_tenant"),)


class SessionModel(Base):
    __tablename__ = "sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.package_id"), nullable=False, index=True
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(32), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), index=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.pending, nullable=False, index=True
    )
    last_reconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")
    package: Mapped[Package] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_lookup", "tenant_id", "phone", "status", "end_time"),
        Index("ix_sessions_mac_ip", "tenant_id", "mac_address", "ip_address"),
    )


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.package_id"), nullable=False, index=True
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    mpesa_checkout_request_id: Mapped[str | None] = mapped_column(String(128), index=True)
    mpesa_receipt: Mapped[str | None] = mapped_column(String(64), index=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="payments")
    package: Mapped[Package] = relationship(back_populates="payments")


class Device(Base):
    __tablename__ = "devices"

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    device_type: Mapped[str] = mapped_column(String(64), nullable=False, default="mikrotik")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mac: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus), default=DeviceStatus.offline, nullable=False
    )
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("tenant_id", "mac", name="uq_device_mac_tenant"),)


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.open, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=False, index=True
    )
    sender: Mapped[str] = mapped_column(String(120), nullable=False)
    receiver: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, default="notification")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OTPCode(Base):
    __tablename__ = "otp_codes"

    otp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.tenant_id"), nullable=True, index=True
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lock_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_otp_lookup", "phone", "role", "tenant_id", "used"),
    )
