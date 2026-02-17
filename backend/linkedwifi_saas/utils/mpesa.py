from __future__ import annotations

import base64
from datetime import datetime

import httpx
from fastapi import HTTPException

from ..database import settings


async def get_access_token() -> str:
    auth = (settings.mpesa_consumer_key, settings.mpesa_consumer_secret)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{settings.mpesa_base_url}/oauth/v1/generate?grant_type=client_credentials",
            auth=auth,
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"M-Pesa auth failed: {response.text}")
    return response.json()["access_token"]


async def stk_push(phone: str, amount: float, account_reference: str, transaction_desc: str) -> dict:
    token = await get_access_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{settings.mpesa_shortcode}{settings.mpesa_passkey}{timestamp}".encode("utf-8")
    ).decode("utf-8")
    payload = {
        "BusinessShortCode": settings.mpesa_shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.mpesa_shortcode,
        "PhoneNumber": phone,
        "CallBackURL": settings.mpesa_callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc,
    }
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{settings.mpesa_base_url}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"M-Pesa STK push failed: {response.text}")
    return response.json()

