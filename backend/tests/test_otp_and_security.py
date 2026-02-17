from linkedwifi_saas.models import Role
from linkedwifi_saas.security import create_access_token, decode_access_token
from linkedwifi_saas.utils.otp import generate_otp, hash_otp, verify_otp


def test_otp_roundtrip() -> None:
    otp = generate_otp()
    assert len(otp) == 6
    hashed = hash_otp(otp)
    assert verify_otp(otp, hashed) is True
    assert verify_otp("000000", hashed) is False


def test_access_token_roundtrip() -> None:
    token = create_access_token(
        account_id="00000000-0000-0000-0000-000000000001",
        role=Role.super_admin,
        tenant_id=None,
    )
    payload = decode_access_token(token)
    assert payload["role"] == "super_admin"

