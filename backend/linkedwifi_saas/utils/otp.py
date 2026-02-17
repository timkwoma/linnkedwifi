from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext

# NOTE:
# bcrypt backend combinations on some platforms can raise runtime errors
# unrelated to OTP length (e.g. backend compatibility checks).
# OTP codes are short-lived, so pbkdf2_sha256 is sufficient and stable.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def generate_otp() -> str:
    return f"{random.randint(100000, 999999)}"


def hash_otp(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_otp(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def otp_expiry(expiry_seconds: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=expiry_seconds)
