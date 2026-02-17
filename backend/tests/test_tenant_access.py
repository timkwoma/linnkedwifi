from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from linkedwifi_saas.models import Role
from linkedwifi_saas.routers import payments as payments_router
from linkedwifi_saas.schemas import MpesaSTKPushIn
from linkedwifi_saas.security import enforce_tenant_access


def test_enforce_tenant_access_allows_super_admin() -> None:
    account = SimpleNamespace(role=Role.super_admin, tenant_id=None)
    enforce_tenant_access(account, uuid4())


def test_enforce_tenant_access_allows_matching_isp_admin_tenant() -> None:
    tenant_id = uuid4()
    account = SimpleNamespace(role=Role.isp_admin, tenant_id=tenant_id)
    enforce_tenant_access(account, tenant_id)


def test_enforce_tenant_access_blocks_mismatched_isp_admin_tenant() -> None:
    account = SimpleNamespace(role=Role.isp_admin, tenant_id=uuid4())
    with pytest.raises(HTTPException) as exc:
        enforce_tenant_access(account, uuid4())
    assert exc.value.status_code == 403


def test_user_cannot_initiate_payment_for_other_phone() -> None:
    tenant_id = uuid4()
    account = SimpleNamespace(role=Role.user, tenant_id=tenant_id, phone="+254700000001")
    payload = MpesaSTKPushIn(
        tenant_id=tenant_id,
        phone="+254700000002",
        package_id=uuid4(),
    )
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(payments_router.initiate_stk_push(payload, db, account))

    assert exc.value.status_code == 403
