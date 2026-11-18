import hashlib
import hmac
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.payment_models import PaymentAllocation, PaymentTransaction
from app.payment_service import record_payment, record_refund

router = APIRouter(prefix="/payments", tags=["payments"])


def _is_admin(user: User) -> bool:
    return any(role.role == "admin" for role in user.roles)


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    x_payment_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    secret = get_settings().payment_webhook_secret
    if not secret:
        raise HTTPException(status_code=503, detail="Төлбөрийн webhook secret тохируулаагүй байна.")
    raw = await request.body()
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    supplied = (x_payment_signature or "").removeprefix("sha256=").strip()
    if not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Webhook гарын үсэг буруу байна.")
    try:
        event = json.loads(raw)
        provider = str(event["provider"]).strip()
        event_type = str(event["event_type"]).strip()
        external_payment_id = str(event["payment_id"]).strip()
        if not provider or not external_payment_id or len(provider) > 60 or len(external_payment_id) > 160:
            raise ValueError("invalid identifier")
        if event_type == "payment.succeeded":
            payment, created = record_payment(
                db, provider=provider, external_payment_id=external_payment_id,
                order_type=str(event["order_type"])[:60], order_id=str(event["order_id"])[:100],
                category=str(event["category"])[:80], buyer_user_id=int(event["buyer_user_id"]),
                provider_user_id=int(event["provider_user_id"]), amount=int(event["amount"]),
            )
        elif event_type == "payment.refunded":
            payment, created = record_refund(
                db, provider=provider, external_payment_id=external_payment_id,
                external_event_id=str(event["event_id"])[:120],
                refund_amount=int(event["refund_amount"]),
            )
        else:
            # Pending/failed events never create commission entries.
            return {"accepted": True, "recorded": False, "reason": "non-settlement event"}
        db.commit()
        db.refresh(payment)
        return {"accepted": True, "recorded": created, "payment_id": payment.id, "status": payment.status}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        db.rollback()
        raise HTTPException(status_code=422, detail="Webhook өгөгдөл дутуу эсвэл буруу байна.")
    except Exception:
        db.rollback()
        raise


@router.get("/admin/summary")
def commission_admin_summary(
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    admin: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(admin):
        raise HTTPException(status_code=403, detail="Зөвхөн админ үзнэ.")
    query = db.query(PaymentTransaction)
    if from_date:
        query = query.filter(PaymentTransaction.paid_at >= from_date)
    if to_date:
        query = query.filter(PaymentTransaction.paid_at <= to_date)
    rows = query.all()
    paid = sum(p.gross_amount for p in rows)
    refunded = sum(p.refunded_amount for p in rows)
    commission = sum(p.commission_amount - p.refunded_commission for p in rows)
    provider_net = sum(p.provider_net_amount - (p.refunded_amount - p.refunded_commission) for p in rows)
    categories = {}
    for p in rows:
        item = categories.setdefault(p.category, {"gross": 0, "commission": 0, "provider_net": 0, "refund": 0})
        item["gross"] += p.gross_amount
        item["commission"] += p.commission_amount - p.refunded_commission
        item["provider_net"] += p.provider_net_amount - (p.refunded_amount - p.refunded_commission)
        item["refund"] += p.refunded_amount
    return {
        "commission_rate_percent": 5,
        "gross_paid_mnt": paid,
        "refunded_mnt": refunded,
        "platform_commission_mnt": commission,
        "provider_net_after_refunds_mnt": provider_net,
        "transactions": len(rows),
        "categories": categories,
    }


@router.get("/provider/summary")
def provider_commission_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(PaymentTransaction).filter(PaymentTransaction.provider_user_id == user.id).all()
    return {
        "gross_paid_mnt": sum(p.gross_amount for p in rows),
        "commission_deducted_mnt": sum(p.commission_amount - p.refunded_commission for p in rows),
        "refunds_mnt": sum(p.refunded_amount for p in rows),
        "net_after_commission_and_refunds_mnt": sum(p.provider_net_amount - (p.refunded_amount - p.refunded_commission) for p in rows),
        "transactions": len(rows),
    }
