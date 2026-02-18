from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import create_engine, text

from ..database import settings

logger = logging.getLogger(__name__)

radius_engine = create_engine(
    settings.radius_db_url or settings.database_url, pool_pre_ping=True
)


def _upsert_radcheck(phone: str, attribute: str, op: str, value: str) -> None:
    with radius_engine.begin() as conn:
        conn.execute(
            text(
                """
                delete from radcheck where username = :username and attribute = :attribute;
                insert into radcheck (username, attribute, op, value)
                values (:username, :attribute, :op, :value);
                """
            ),
            {
                "username": phone,
                "attribute": attribute,
                "op": op,
                "value": value,
            },
        )


def _upsert_radreply(phone: str, attribute: str, op: str, value: str) -> None:
    with radius_engine.begin() as conn:
        conn.execute(
            text(
                """
                delete from radreply where username = :username and attribute = :attribute;
                insert into radreply (username, attribute, op, value)
                values (:username, :attribute, :op, :value);
                """
            ),
            {
                "username": phone,
                "attribute": attribute,
                "op": op,
                "value": value,
            },
        )


def authorize_session(
    phone: str,
    mac_address: str | None,
    ip_address: str | None,
    expires_at: datetime,
) -> None:
    # Uses radcheck/radreply tables used by FreeRADIUS SQL module.
    _upsert_radcheck(phone, "Cleartext-Password", ":=", phone)
    if mac_address:
        _upsert_radcheck(phone, "Calling-Station-Id", "==", mac_address)
    if ip_address:
        _upsert_radreply(phone, "Framed-IP-Address", ":=", ip_address)
    _upsert_radreply(
        phone, "WISPr-Session-Terminate-Time", ":=", expires_at.isoformat()
    )
    logger.info(
        "FreeRADIUS authorize: phone=%s mac=%s ip=%s expires_at=%s",
        phone,
        mac_address,
        ip_address,
        expires_at.isoformat(),
    )


def block_session(phone: str) -> None:
    with radius_engine.begin() as conn:
        conn.execute(
            text("delete from radcheck where username = :username"), {"username": phone}
        )
        conn.execute(
            text("delete from radreply where username = :username"), {"username": phone}
        )
    logger.info("FreeRADIUS block: phone=%s", phone)
