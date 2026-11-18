import hashlib
import hmac
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.payment_models import PaymentAllocation, PaymentTransaction
from app.payment_service import record_payment, record_refund
from app.qpay_client import check_invoice, create_invoice
from app.qpay_models import QPayInvoice
from app.ecosystem_models import (
    Club, ClubMembership, Notification, Product, ShopOrder, ShopOrderItem,
)
from app.referee_models import RefereeBooking
from app.service_models import ServiceProvider, ServiceRequest
from app.venue_models import VenueBooking, VenueSlot

router = APIRouter(prefix="/payments", tags=["payments"])


class QPayInvoiceInput(BaseModel):
    order_type: str = Field(pattern="^(store_order|referee_booking|venue_booking|service_request|club_membership)$")
    order_id: int = Field(gt=0)


def _is_admin(user: User) -> bool:
    return any(role.role == "admin" for role in user.roles)


def _notify(db: Session, user_id: int, title: str, body: str, category: str = "payment"):
    db.add(Notification(user_id=user_id, title=title, body=body[:1000], category=category))


def _order_for_payment(db: Session, user: User, order_type: str, order_id: int):
    allocations: dict[int, int] = {}
    if order_type == "store_order":
        order = db.get(ShopOrder, order_id)
        if order is None or order.user_id != user.id:
            raise HTTPException(status_code=404, detail="Дэлгүүрийн захиалга олдсонгүй.")
        if order.status != "pending_payment" or order.payment_status != "unpaid":
            raise HTTPException(status_code=409, detail="Энэ захиалга төлбөр хүлээн авах төлөвт биш байна.")
        items = db.query(ShopOrderItem).filter_by(order_id=order.id).all()
        for line in items:
            product = db.get(Product, line.product_id) if line.product_id else None
            if product is None:
                raise HTTPException(status_code=409, detail="Захиалгын барааны эзэмшигч тодорхойгүй байна.")
            allocations[product.seller_id] = allocations.get(product.seller_id, 0) + line.unit_price * line.quantity
        category = "sports_store"
        amount = order.total_amount
        description = f"ARENA 360 дэлгүүрийн захиалга #{order.id}"
    elif order_type == "referee_booking":
        order = db.get(RefereeBooking, order_id)
        if order is None or order.requester_id != user.id:
            raise HTTPException(status_code=404, detail="Шүүгчийн захиалга олдсонгүй.")
        if order.status not in {"assigned", "accepted"} or not order.referee_user_id:
            raise HTTPException(status_code=409, detail="Төлбөр хийхээс өмнө шүүгч томилогдсон байх шаардлагатай.")
        if order.payment_status == "paid":
            raise HTTPException(status_code=409, detail="Энэ захиалгын төлбөр аль хэдийн төлөгдсөн.")
        amount = order.referee_count * order.unit_fee * order.work_days + order.transport_fee + order.food_fee
        allocations[order.referee_user_id] = amount
        category = "referee"
        description = f"ARENA 360 шүүгчийн үйлчилгээ #{order.id}"
    elif order_type == "venue_booking":
        order = db.get(VenueBooking, order_id)
        if order is None or order.customer_id != user.id:
            raise HTTPException(status_code=404, detail="Заалын захиалга олдсонгүй.")
        if order.status != "pending" or order.payment_status == "paid":
            raise HTTPException(status_code=409, detail="Энэ заалын захиалга төлбөр хүлээн авах төлөвт биш байна.")
        slot = db.get(VenueSlot, order.slot_id)
        if slot is None:
            raise HTTPException(status_code=404, detail="Заалын цаг олдсонгүй.")
        amount = slot.price
        allocations[order.provider_user_id] = amount
        category = "venue_booking"
        description = f"ARENA 360 заал түрээс #{order.id}"
    elif order_type == "service_request":
        order = db.get(ServiceRequest, order_id)
        if order is None or order.requester_id != user.id:
            raise HTTPException(status_code=404, detail="Үйлчилгээний хүсэлт олдсонгүй.")
        if order.status != "accepted" or not order.provider_user_id or order.payment_status == "paid":
            raise HTTPException(status_code=409, detail="Үйлчилгээ үзүүлэгч хүсэлтийг зөвшөөрсний дараа төлбөр хийнэ.")
        provider = db.query(ServiceProvider).filter(
            ServiceProvider.user_id == order.provider_user_id,
            ServiceProvider.category == order.category,
            ServiceProvider.verification_status == "verified",
        ).first()
        if provider is None:
            raise HTTPException(status_code=404, detail="Баталгаажсан үйлчилгээ үзүүлэгч олдсонгүй.")
        amount = provider.price_from
        allocations[provider.user_id] = amount
        category = order.category
        description = f"ARENA 360 үйлчилгээ #{order.id}"
    else:
        membership = db.get(ClubMembership, order_id)
        if membership is None or membership.user_id != user.id:
            raise HTTPException(status_code=404, detail="Клубын гишүүнчлэлийн хүсэлт олдсонгүй.")
        club = db.get(Club, membership.club_id)
        if club is None or club.membership_fee <= 0 or membership.status != "pending_payment":
            raise HTTPException(status_code=409, detail="Энэ клубын хүсэлт төлбөр шаардахгүй эсвэл төлбөрийн төлөвт биш байна.")
        amount = club.membership_fee
        allocations[club.owner_id] = amount
        category = "club_membership"
        description = f"ARENA 360 {club.name} клубын гишүүнчлэл"

    if amount <= 0 or sum(allocations.values()) != amount:
        raise HTTPException(status_code=422, detail="Захиалгын төлбөрийн дүн буруу байна.")
    return {
        "amount": amount,
        "category": category,
        "description": description,
        "allocations": [{"provider_user_id": uid, "gross_amount": gross} for uid, gross in sorted(allocations.items())],
    }


def _mark_order_paid(db: Session, invoice: QPayInvoice):
    order_id = int(invoice.order_id)
    if invoice.order_type == "store_order":
        order = db.get(ShopOrder, order_id)
        if order and order.payment_status != "paid":
            order.payment_status = "paid"
            order.status = "paid"
            buyer = db.get(User, order.user_id)
            lines = db.query(ShopOrderItem).filter_by(order_id=order.id).all()
            for line in lines:
                product = db.get(Product, line.product_id) if line.product_id else None
                if product:
                    _notify(db, product.seller_id, "Төлбөр баталгаажсан захиалга",
                            f"{line.product_title} × {line.quantity}. Захиалагч: {buyer.phone if buyer else order.contact_phone}. Захиалгын №{order.id}. Хүргэлт: {order.delivery_address}", "order")
    elif invoice.order_type == "referee_booking":
        order = db.get(RefereeBooking, order_id)
        if order and order.payment_status != "paid":
            order.payment_status = "paid"
            if order.referee_user_id:
                _notify(db, order.referee_user_id, "Шүүгчийн үйлчилгээний төлбөр төлөгдлөө",
                        f"Захиалга №{order.id} төлбөр баталгаажлаа.", "referee")
    elif invoice.order_type == "venue_booking":
        order = db.get(VenueBooking, order_id)
        if order and order.payment_status != "paid":
            order.payment_status = "paid"
            _notify(db, order.provider_user_id, "Заалын захиалгын төлбөр төлөгдлөө",
                    f"Заалын захиалга №{order.id} төлбөр баталгаажлаа.", "venue")
    elif invoice.order_type == "service_request":
        order = db.get(ServiceRequest, order_id)
        if order and order.payment_status != "paid":
            order.payment_status = "paid"
            if order.provider_user_id:
                _notify(db, order.provider_user_id, "Үйлчилгээний төлбөр төлөгдлөө",
                        f"Үйлчилгээний хүсэлт №{order.id} төлбөр баталгаажлаа.", "service")
    elif invoice.order_type == "club_membership":
        membership = db.get(ClubMembership, order_id)
        if membership and membership.payment_status != "paid":
            membership.payment_status = "paid"
            membership.status = "pending"
            club = db.get(Club, membership.club_id)
            if club:
                _notify(db, club.owner_id, "Клубын гишүүнчлэлийн төлбөр төлөгдлөө",
                        f"{club.name} клубт шинэ төлбөртэй элсэх хүсэлт ирлээ.", "club")


@router.post("/qpay/invoice", status_code=201)
def create_qpay_invoice(
    payload: QPayInvoiceInput,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order_data = _order_for_payment(db, user, payload.order_type, payload.order_id)
    sender_no = f"AR360-{uuid4().hex}"
    settings = get_settings()
    callback_base = settings.qpay_callback_url.rstrip("/")
    if not callback_base.startswith("https://"):
        raise HTTPException(status_code=503, detail="QP AY_CALLBACK_URL-г HTTPS хаягаар тохируулна уу.")
    callback_url = f"{callback_base}/api/v1/payments/qpay/callback/{sender_no}"
    result = create_invoice(
        sender_invoice_no=sender_no,
        description=order_data["description"],
        amount=order_data["amount"],
        callback_url=callback_url,
    )
    external_invoice_id = result.get("invoice_id")
    if not external_invoice_id:
        raise HTTPException(status_code=502, detail="QPay нэхэмжлэлийн дугаар буцаасангүй.")
    invoice = QPayInvoice(
        user_id=user.id,
        order_type=payload.order_type,
        order_id=str(payload.order_id),
        qpay_invoice_id=str(external_invoice_id),
        sender_invoice_no=sender_no,
        amount=order_data["amount"],
        status="pending",
        qr_text=result.get("qr_text"),
        qr_image=result.get("qr_image"),
        short_url=result.get("qPay_shortUrl") or result.get("qpay_short_url"),
        bank_links_json=json.dumps(result.get("urls", []), ensure_ascii=False),
        allocations_json=json.dumps(order_data["allocations"]),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return {
        "id": invoice.id,
        "provider": "qpay",
        "status": invoice.status,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "invoice_id": invoice.qpay_invoice_id,
        "qr_text": invoice.qr_text,
        "qr_image": invoice.qr_image,
        "short_url": invoice.short_url,
        "bank_links": json.loads(invoice.bank_links_json or "[]"),
        "callback_url": callback_url,
    }


def _confirm_qpay_invoice(db: Session, invoice: QPayInvoice):
    if invoice.status == "paid":
        return {"status": "paid", "already_confirmed": True}
    result = check_invoice(invoice.qpay_invoice_id)
    rows = result.get("rows") or []
    paid_rows = [row for row in rows if str(row.get("payment_status", "")).upper() == "PAID"]
    if not paid_rows:
        return {"status": "pending", "already_confirmed": False}
    currencies = {str(row.get("payment_currency", "MNT")).upper() for row in paid_rows}
    try:
        paid_amount = Decimal(str(result.get("paid_amount", "0")))
    except InvalidOperation as exc:
        raise HTTPException(status_code=502, detail="QPay төлбөрийн дүнг уншиж чадсангүй.") from exc
    if currencies != {"MNT"} or paid_amount != Decimal(invoice.amount):
        raise HTTPException(status_code=409, detail="QPay төлсөн дүн эсвэл валют захиалгын дүнтэй таарахгүй байна.")
    payment_ids = sorted({str(row.get("payment_id", "")) for row in paid_rows if row.get("payment_id")})
    if not payment_ids:
        raise HTTPException(status_code=502, detail="QPay баталгаажсан гүйлгээний дугаар буцаасангүй.")
    allocations = json.loads(invoice.allocations_json or "[]")
    provider_ids = {int(x["provider_user_id"]) for x in allocations}
    payment, created = record_payment(
        db,
        provider="qpay",
        external_payment_id=invoice.qpay_invoice_id,
        order_type=invoice.order_type,
        order_id=invoice.order_id,
        category=invoice.order_type.replace("_", " "),
        buyer_user_id=invoice.user_id,
        provider_user_id=next(iter(provider_ids)) if len(provider_ids) == 1 else None,
        amount=invoice.amount,
        allocations=allocations,
    )
    invoice.status = "paid"
    invoice.qpay_payment_id = ",".join(payment_ids)[:160]
    invoice.paid_at = datetime.now(timezone.utc)
    _mark_order_paid(db, invoice)
    return {"status": "paid", "already_confirmed": not created, "payment_record_id": payment.id}


@router.post("/qpay/callback/{sender_invoice_no}")
def qpay_callback(sender_invoice_no: str, db: Session = Depends(get_db)):
    invoice = db.query(QPayInvoice).filter_by(sender_invoice_no=sender_invoice_no).with_for_update().first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="QPay нэхэмжлэл олдсонгүй.")
    result = _confirm_qpay_invoice(db, invoice)
    db.commit()
    return {"accepted": True, **result}


@router.post("/qpay/invoices/{invoice_id}/check")
def check_qpay_invoice(
    invoice_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.get(QPayInvoice, invoice_id)
    if invoice is None or (invoice.user_id != user.id and not _is_admin(user)):
        raise HTTPException(status_code=404, detail="Төлбөрийн нэхэмжлэл олдсонгүй.")
    result = _confirm_qpay_invoice(db, invoice)
    db.commit()
    return {"id": invoice.id, **result}


@router.get("/qpay/invoices/{invoice_id}")
def get_qpay_invoice(
    invoice_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.get(QPayInvoice, invoice_id)
    if invoice is None or (invoice.user_id != user.id and not _is_admin(user)):
        raise HTTPException(status_code=404, detail="Төлбөрийн нэхэмжлэл олдсонгүй.")
    return {
        "id": invoice.id, "order_type": invoice.order_type, "order_id": invoice.order_id,
        "amount": invoice.amount, "currency": invoice.currency, "status": invoice.status,
        "qr_text": invoice.qr_text, "qr_image": invoice.qr_image,
        "short_url": invoice.short_url, "bank_links": json.loads(invoice.bank_links_json or "[]"),
    }


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    x_payment_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    # Generic signed provider webhook retained for non-QPay adapters.
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
    rows = db.query(PaymentAllocation).filter(PaymentAllocation.provider_user_id == user.id).all()
    return {
        "gross_paid_mnt": sum(p.gross_amount for p in rows),
        "commission_deducted_mnt": sum(p.commission_amount - p.refunded_commission for p in rows),
        "refunds_mnt": sum(p.refunded_amount for p in rows),
        "net_after_commission_and_refunds_mnt": sum(p.provider_net_amount - (p.refunded_amount - p.refunded_commission) for p in rows),
        "transactions": len(rows),
    }
