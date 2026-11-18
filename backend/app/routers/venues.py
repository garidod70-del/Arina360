from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.service_models import ServiceProvider
from app.venue_models import VenueBooking, VenueSlot
from app.venue_schemas import (
    VenueBookingDecision, VenueBookingInput, VenueBookingOutput,
    VenueSlotInput, VenueSlotOutput,
)

router = APIRouter(prefix="/venues", tags=["venue-booking"])


def _is_admin(user: User) -> bool:
    return any(role.role == "admin" for role in user.roles)


def _slot_output(item: VenueSlot) -> VenueSlotOutput:
    return VenueSlotOutput(
        id=item.id, provider_user_id=item.provider_user_id, venue_name=item.venue_name,
        venue_address=item.venue_address, sport=item.sport, booking_date=item.booking_date,
        start_time=item.start_time, end_time=item.end_time, price=item.price,
        notes=item.notes, status=item.status,
    )


def _booking_output(item: VenueBooking) -> VenueBookingOutput:
    return VenueBookingOutput(
        id=item.id, slot_id=item.slot_id, customer_id=item.customer_id,
        provider_user_id=item.provider_user_id, contact_phone=item.contact_phone,
        purpose=item.purpose, status=item.status, payment_status=item.payment_status, created_at=item.created_at,
    )


@router.get("/slots", response_model=list[VenueSlotOutput])
def list_venue_slots(
    booking_date: date = Query(),
    sport: str | None = Query(default=None, max_length=80),
    region: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    query = db.query(VenueSlot).join(
        ServiceProvider,
        (ServiceProvider.user_id == VenueSlot.provider_user_id) & (ServiceProvider.category == "venue_booking"),
    ).filter(
        VenueSlot.booking_date == booking_date,
        VenueSlot.status == "available",
        ServiceProvider.verification_status == "verified",
    )
    if sport:
        query = query.filter(VenueSlot.sport.ilike(f"%{sport}%"))
    if region:
        query = query.filter(VenueSlot.venue_address.ilike(f"%{region}%"))
    return [_slot_output(item) for item in query.order_by(VenueSlot.start_time).limit(200).all()]


@router.post("/slots", response_model=VenueSlotOutput, status_code=201)
def create_venue_slot(
    payload: VenueSlotInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = db.query(ServiceProvider).filter(
        ServiceProvider.user_id == user.id,
        ServiceProvider.category == "venue_booking",
        ServiceProvider.verification_status == "verified",
    ).first()
    if provider is None:
        raise HTTPException(status_code=403, detail="Заалын үйлчилгээ үзүүлэгчийн баталгаажсан бүртгэл шаардлагатай.")
    if payload.booking_date < date.today():
        raise HTTPException(status_code=400, detail="Өнгөрсөн өдөрт цаг нэмэх боломжгүй.")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="Дуусах цаг эхлэх цагаас хойш байх ёстой.")
    overlap = db.query(VenueSlot).filter(
        VenueSlot.provider_user_id == user.id,
        VenueSlot.venue_name == payload.venue_name,
        VenueSlot.booking_date == payload.booking_date,
        VenueSlot.status == "available",
        VenueSlot.start_time < payload.end_time,
        VenueSlot.end_time > payload.start_time,
    ).first()
    if overlap:
        raise HTTPException(status_code=409, detail="Энэ цагтай давхцсан сул цаг аль хэдийн бүртгэгдсэн байна.")
    item = VenueSlot(provider_user_id=user.id, **payload.model_dump(), status="available")
    db.add(item)
    db.commit()
    db.refresh(item)
    return _slot_output(item)


@router.get("/slots/me", response_model=list[VenueSlotOutput])
def list_my_venue_slots(
    booking_date: date | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(VenueSlot).filter(VenueSlot.provider_user_id == user.id)
    if booking_date:
        query = query.filter(VenueSlot.booking_date == booking_date)
    return [_slot_output(item) for item in query.order_by(VenueSlot.booking_date, VenueSlot.start_time).limit(300).all()]


@router.post("/slots/{slot_id}/book", response_model=VenueBookingOutput, status_code=201)
def book_venue_slot(
    slot_id: int,
    payload: VenueBookingInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    slot = db.query(VenueSlot).filter(VenueSlot.id == slot_id).with_for_update().first()
    if slot is None or slot.status != "available":
        raise HTTPException(status_code=409, detail="Энэ цаг сул биш эсвэл олдсонгүй.")
    if slot.provider_user_id == user.id:
        raise HTTPException(status_code=400, detail="Өөрийн заалыг өөрөө захиалах боломжгүй.")
    provider = db.query(ServiceProvider).filter(
        ServiceProvider.user_id == slot.provider_user_id,
        ServiceProvider.category == "venue_booking",
        ServiceProvider.verification_status == "verified",
    ).first()
    if provider is None:
        raise HTTPException(status_code=404, detail="Баталгаажсан заалын үйлчилгээ үзүүлэгч олдсонгүй.")
    pending = db.query(VenueBooking).filter(
        VenueBooking.slot_id == slot.id,
        VenueBooking.status.in_(["pending", "confirmed"]),
    ).first()
    if pending:
        raise HTTPException(status_code=409, detail="Энэ цагт захиалга аль хэдийн үүссэн байна.")
    item = VenueBooking(
        slot_id=slot.id, customer_id=user.id, provider_user_id=slot.provider_user_id,
        contact_phone=payload.contact_phone, purpose=payload.purpose, status="pending",
    )
    slot.status = "reserved"
    db.add(item)
    db.commit()
    db.refresh(item)
    return _booking_output(item)


@router.get("/bookings/me", response_model=list[VenueBookingOutput])
def list_my_venue_bookings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(VenueBooking).filter(
        (VenueBooking.customer_id == user.id) | (VenueBooking.provider_user_id == user.id)
    ).order_by(VenueBooking.created_at.desc()).limit(200).all()
    return [_booking_output(item) for item in rows]


@router.post("/bookings/{booking_id}/decision", response_model=VenueBookingOutput)
def decide_venue_booking(
    booking_id: int,
    payload: VenueBookingDecision,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(VenueBooking).filter(VenueBooking.id == booking_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Заалын захиалга олдсонгүй.")
    if item.provider_user_id != user.id and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Зөвхөн заалын эзэмшигч захиалгыг шийдвэрлэнэ.")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Энэ захиалгыг өмнө нь шийдвэрлэсэн байна.")
    slot = db.query(VenueSlot).filter(VenueSlot.id == item.slot_id).first()
    if payload.accepted:
        item.status = "confirmed"
        if slot and slot.price <= 0:
            item.payment_status = "free"
        if slot:
            slot.status = "booked"
    else:
        item.status = "rejected"
        if slot:
            slot.status = "available"
    if payload.note:
        item.purpose = (item.purpose or "") + "\nХариу: " + payload.note
    db.commit()
    db.refresh(item)
    return _booking_output(item)


@router.post("/bookings/{booking_id}/cancel", response_model=VenueBookingOutput)
def cancel_venue_booking(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(VenueBooking).filter(VenueBooking.id == booking_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Заалын захиалга олдсонгүй.")
    if item.customer_id != user.id and item.provider_user_id != user.id and not _is_admin(user):
        raise HTTPException(status_code=403, detail="Энэ захиалгыг цуцлах эрхгүй.")
    if item.status not in {"pending", "confirmed"}:
        raise HTTPException(status_code=409, detail="Энэ захиалгыг цуцлах боломжгүй.")
    item.status = "cancelled"
    slot = db.query(VenueSlot).filter(VenueSlot.id == item.slot_id).first()
    if slot:
        slot.status = "available"
    db.commit()
    db.refresh(item)
    return _booking_output(item)
