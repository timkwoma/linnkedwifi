from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .database import get_db, settings
from .models import Account, Role

bearer_scheme = HTTPBearer(auto_error=True)


def create_access_token(account_id: UUID, role: Role, tenant_id: UUID | None) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(hours=12)
    payload = {
        "sub": str(account_id),
        "role": role.value,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "exp": expire_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc


def get_current_account(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Account:
    payload = decode_access_token(creds.credentials)
    account = db.get(Account, UUID(str(payload["sub"])))
    if not account or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found"
        )
    return account


def require_role(*roles: Role):
    def _guard(account: Account = Depends(get_current_account)) -> Account:
        if account.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return account

    return _guard


def enforce_tenant_access(account: Account, tenant_id: UUID) -> None:
    if account.role == Role.super_admin:
        return
    if account.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied"
        )
