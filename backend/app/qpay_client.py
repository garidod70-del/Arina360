"""QPay Merchant V2 client. Credentials and tokens stay on the API server."""
import base64
import threading
import time
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import get_settings

_token_lock = threading.Lock()
_cached_token: str | None = None
_token_expires_at = 0.0


def _base_url() -> str:
    settings = get_settings()
    return settings.qpay_base_url.rstrip("/")


def _request_token(force: bool = False) -> str:
    global _cached_token, _token_expires_at
    settings = get_settings()
    if not settings.qpay_client_id or not settings.qpay_client_secret:
        raise HTTPException(status_code=503, detail="QPay мерчантын эрхийн тохиргоо дутуу байна.")
    with _token_lock:
        if not force and _cached_token and time.time() < _token_expires_at - 60:
            return _cached_token
        credentials = base64.b64encode(
            f"{settings.qpay_client_id}:{settings.qpay_client_secret}".encode()
        ).decode()
        try:
            response = httpx.post(
                f"{_base_url()}/v2/auth/token",
                headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"},
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="QPay нэвтрэлт амжилтгүй боллоо.") from exc
        token = data.get("access_token")
        if not token:
            raise HTTPException(status_code=502, detail="QPay access token буцаасангүй.")
        _cached_token = str(token)
        # QPay expires_in is an absolute Unix timestamp; do not assume a fixed TTL.
        try:
            _token_expires_at = float(data.get("expires_in", time.time() + 300))
        except (TypeError, ValueError):
            _token_expires_at = time.time() + 300
        return _cached_token


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(2):
        token = _request_token(force=attempt == 1)
        try:
            response = httpx.post(
                f"{_base_url()}{path}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=20.0,
            )
            if response.status_code in (401, 403) and attempt == 0:
                continue
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("QPay response must be an object")
            return data
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="QPay үйлчилгээтэй холбогдоход алдаа гарлаа.") from exc
    raise HTTPException(status_code=502, detail="QPay нэвтрэх эрхийг шинэчилж чадсангүй.")


def create_invoice(*, sender_invoice_no: str, description: str, amount: int, callback_url: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.qpay_invoice_code or not callback_url.startswith("https://"):
        raise HTTPException(status_code=503, detail="QPay invoice code болон HTTPS callback URL тохируулах шаардлагатай.")
    return _post("/v2/invoice", {
        "invoice_code": settings.qpay_invoice_code,
        "sender_invoice_no": sender_invoice_no,
        "invoice_receiver_code": "terminal",
        "invoice_description": description[:255],
        "amount": amount,
        "callback_url": callback_url,
    })


def check_invoice(invoice_id: str) -> dict[str, Any]:
    return _post("/v2/payment/check", {
        "object_type": "INVOICE",
        "object_id": invoice_id,
        "offset": {"page_number": 1, "page_limit": 100},
    })
