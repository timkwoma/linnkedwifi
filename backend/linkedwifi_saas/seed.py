from __future__ import annotations

from decimal import Decimal

from sqlalchemy import inspect, select, text

from .database import Base, SessionLocal, engine
from .models import (
    Account,
    Device,
    DeviceStatus,
    Package,
    PackageCategory,
    Role,
    Tenant,
    User,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_otp_schema_compatibility()


def _ensure_otp_schema_compatibility() -> None:
    """Bring older local DBs up to date for OTP lockout fields."""
    insp = inspect(engine)
    if "otp_codes" not in insp.get_table_names():
        return

    columns = {c["name"] for c in insp.get_columns("otp_codes")}
    with engine.begin() as conn:
        if "failed_attempts" not in columns:
            conn.execute(
                text("alter table otp_codes add column failed_attempts int not null default 0")
            )
        if "lock_until" not in columns:
            conn.execute(text("alter table otp_codes add column lock_until timestamptz"))

        indexes = {idx["name"] for idx in insp.get_indexes("otp_codes")}
        if "ix_otp_lookup" not in indexes:
            conn.execute(
                text(
                    "create index if not exists ix_otp_lookup "
                    "on otp_codes (phone, role, tenant_id, used)"
                )
            )


def seed_data() -> None:
    db = SessionLocal()
    try:
        tenant = db.scalar(select(Tenant).where(Tenant.email == "ops@linkedwifi.test"))
        if tenant:
            return

        tenant = Tenant(name="LinkedWiFi Demo ISP", email="ops@linkedwifi.test", plan="pro")
        db.add(tenant)
        db.flush()

        demo_tenant_2 = Tenant(name="MetroNet ISP", email="admin@metronet.test", plan="starter")
        db.add(demo_tenant_2)
        db.flush()

        super_admin = Account(
            role=Role.super_admin,
            tenant_id=None,
            full_name="Platform Super Admin",
            phone="+254700000001",
            email="superadmin@linkedwifi.test",
        )
        isp_admin = Account(
            role=Role.isp_admin,
            tenant_id=tenant.tenant_id,
            full_name="Demo ISP Admin",
            phone="+254700000002",
            email="ispadmin@linkedwifi.test",
        )
        db.add_all([super_admin, isp_admin])

        demo_user = User(
            tenant_id=tenant.tenant_id,
            phone="+254700100001",
            mac_address="AA:BB:CC:DD:EE:01",
            ip_address="10.5.50.10",
            status="active",
        )
        db.add(demo_user)

        packages = [
            Package(
                tenant_id=tenant.tenant_id,
                name="1 Hour Hotspot",
                duration_minutes=60,
                speed_limit_rx=5_000,
                speed_limit_tx=2_000,
                price=Decimal("20.00"),
                category=PackageCategory.hotspot,
            ),
            Package(
                tenant_id=tenant.tenant_id,
                name="3 Hour Hotspot",
                duration_minutes=180,
                speed_limit_rx=8_000,
                speed_limit_tx=3_000,
                price=Decimal("50.00"),
                category=PackageCategory.hotspot,
            ),
            Package(
                tenant_id=tenant.tenant_id,
                name="12 Hour Hotspot",
                duration_minutes=720,
                speed_limit_rx=10_000,
                speed_limit_tx=4_000,
                price=Decimal("100.00"),
                category=PackageCategory.hotspot,
            ),
            Package(
                tenant_id=tenant.tenant_id,
                name="24 Hour Hotspot",
                duration_minutes=1440,
                speed_limit_rx=15_000,
                speed_limit_tx=5_000,
                price=Decimal("150.00"),
                category=PackageCategory.hotspot,
            ),
            Package(
                tenant_id=tenant.tenant_id,
                name="Monthly Home Router",
                duration_minutes=43_200,
                speed_limit_rx=20_000,
                speed_limit_tx=10_000,
                price=Decimal("2000.00"),
                category=PackageCategory.home,
            ),
        ]
        db.add_all(packages)

        devices = [
            Device(
                tenant_id=tenant.tenant_id,
                device_type="mikrotik",
                name="MikroTik Main AP",
                ip="10.5.50.1",
                mac="AA:AA:AA:AA:AA:01",
                status=DeviceStatus.online,
            ),
            Device(
                tenant_id=tenant.tenant_id,
                device_type="mikrotik",
                name="MikroTik Backup AP",
                ip="10.5.50.2",
                mac="AA:AA:AA:AA:AA:02",
                status=DeviceStatus.offline,
            ),
        ]
        db.add_all(devices)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_data()
    print("Database initialized and seeded.")
