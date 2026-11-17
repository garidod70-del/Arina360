from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.referee_models import RefereeBooking, RefereeProfile, RefereeRating
from app.referee_schemas import (
    RefereeBookingInput, RefereeBookingOutput, RefereeProfileInput,
    RefereeProfileOutput, RefereeRatingInput, RefereeRatingOutput,
)

router = APIRouter(prefix="/referees", tags=["referees"])


def _has_role(user: User, role: str) -> bool:
    return any(item.role == role for item in user.roles)


def _require_referee(user: User) -> None:
    if not _has_role(user, "referee") and not _has_role(user, "admin"):
        raise HTTPException(status_code=403, detail="Шүүгчийн баталгаажсан эрх шаардлагатай.")


def _booking_out(item: RefereeBooking) -> RefereeBookingOutput:
    multiplier = item.work_days if item.payment_type == "Нэг өдрөөр" else 1
    total = item.referee_count * item.unit_fee * multiplier + item.transport_fee + item.food_fee
    return RefereeBookingOutput(
        id=item.id, requester_id=item.requester_id, referee_user_id=item.referee_user_id,
        sport=item.sport, rank=item.rank, booking_type=item.booking_type, event_at=item.event_at,
        venue=item.venue, referee_count=item.referee_count, payment_type=item.payment_type,
        unit_fee=item.unit_fee, work_days=item.work_days, transport_fee=item.transport_fee,
        food_fee=item.food_fee, total_amount=total, contact_name=item.contact_name,
        contact_phone=item.contact_phone, notes=item.notes, status=item.status, created_at=item.created_at,
    )


def _profile_out(db: Session, profile: RefereeProfile) -> RefereeProfileOutput:
    user = db.query(User).filter(User.id == profile.user_id).first()
    full_name = user.profile.full_name if user and user.profile else None
    avg, count = db.query(func.avg(RefereeRating.score), func.count(RefereeRating.id)).filter(
        RefereeRating.referee_user_id == profile.user_id
    ).one()
    return RefereeProfileOutput(
        user_id=profile.user_id, full_name=full_name, sport=profile.sport, rank=profile.rank,
        region=profile.region, bio=profile.bio, base_fee=profile.base_fee,
        license_number=profile.license_number, license_issuer=profile.license_issuer,
        license_expires_at=profile.license_expires_at, verified_at=profile.verified_at,
        verification_status=profile.verification_status,
        average_rating=round(float(avg), 2) if avg is not None else None, rating_count=count or 0,
    )


@router.get("", response_model=list[RefereeProfileOutput])
def list_referees(
    sport: str | None = Query(default=None, max_length=80),
    region: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    query = db.query(RefereeProfile).filter(RefereeProfile.verification_status == "verified")
    if sport:
        query = query.filter(RefereeProfile.sport.ilike(f"%{sport}%"))
    if region:
        query = query.filter(RefereeProfile.region.ilike(f"%{region}%"))
    return [_profile_out(db, item) for item in query.order_by(RefereeProfile.created_at.desc()).limit(100).all()]


@router.post("/profile/me", response_model=RefereeProfileOutput, status_code=201)
def save_referee_profile(
    payload: RefereeProfileInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_referee(user)
    profile = db.query(RefereeProfile).filter(RefereeProfile.user_id == user.id).first()
    if profile is None:
        profile = RefereeProfile(user_id=user.id, **payload.model_dump(), verification_status="pending")
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
        # Any material profile change requires re-verification.
        profile.verification_status = "pending"
    db.commit()
    db.refresh(profile)
    return _profile_out(db, profile)


@router.get("/requests/me", response_model=list[RefereeBookingOutput])
def my_requests(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(RefereeBooking).filter(
        (RefereeBooking.requester_id == user.id) | (RefereeBooking.referee_user_id == user.id)
    ).order_by(RefereeBooking.created_at.desc()).limit(100).all()
    return [_booking_out(item) for item in rows]


@router.post("/requests", response_model=RefereeBookingOutput, status_code=201)
def create_request(
    payload: RefereeBookingInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = RefereeBooking(requester_id=user.id, **payload.model_dump(), status="pending")
    db.add(item)
    db.commit()
    db.refresh(item)
    return _booking_out(item)


@router.post("/requests/{booking_id}/assign", response_model=RefereeBookingOutput)
def assign_referee(
    booking_id: int,
    referee_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(RefereeBooking).filter(RefereeBooking.id == booking_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй.")
    if item.requester_id != user.id and not _has_role(user, "admin"):
        raise HTTPException(status_code=403, detail="Зөвхөн захиалагч эсвэл админ томилгоо хийнэ.")
    if item.status not in {"pending", "assigned"}:
        raise HTTPException(status_code=409, detail="Энэ захиалгад томилгоо хийх боломжгүй.")
    profile = db.query(RefereeProfile).filter(
        RefereeProfile.user_id == referee_user_id,
        RefereeProfile.verification_status == "verified",
    ).first()
    if profile is None or not _has_role(db.query(User).filter(User.id == referee_user_id).first(), "referee"):
        raise HTTPException(status_code=400, detail="Баталгаажсан шүүгчийн профайл олдсонгүй.")
    if profile.sport.casefold() != item.sport.casefold():
        raise HTTPException(status_code=400, detail="Шүүгчийн спортын төрөл тохирохгүй байна.")
    item.referee_user_id = referee_user_id
    item.status = "assigned"
    db.commit()
    db.refresh(item)
    return _booking_out(item)


@router.post("/requests/{booking_id}/accept", response_model=RefereeBookingOutput)
def accept_assignment(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_referee(user)
    item = db.query(RefereeBooking).filter(RefereeBooking.id == booking_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй.")
    if item.referee_user_id != user.id or item.status != "assigned":
        raise HTTPException(status_code=409, detail="Танд оноосон идэвхтэй томилгоо алга.")
    item.status = "accepted"
    db.commit()
    db.refresh(item)
    return _booking_out(item)


@router.post("/requests/{booking_id}/complete", response_model=RefereeBookingOutput)
def complete_assignment(
    booking_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(RefereeBooking).filter(RefereeBooking.id == booking_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй.")
    if user.id not in {item.requester_id, item.referee_user_id} and not _has_role(user, "admin"):
        raise HTTPException(status_code=403, detail="Энэ захиалгыг дуусгах эрхгүй.")
    if item.status != "accepted":
        raise HTTPException(status_code=409, detail="Зөвхөн зөвшөөрсөн томилгоог дуусгана.")
    item.status = "completed"
    db.commit()
    db.refresh(item)
    return _booking_out(item)


@router.post("/requests/{booking_id}/rating", response_model=RefereeRatingOutput, status_code=201)
def rate_referee(
    booking_id: int,
    payload: RefereeRatingInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(RefereeBooking).filter(RefereeBooking.id == booking_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй.")
    if item.requester_id != user.id or item.status != "completed" or item.referee_user_id is None:
        raise HTTPException(status_code=403, detail="Дууссан, шүүгч томилогдсон захиалгыг зөвхөн захиалагч үнэлнэ.")
    if db.query(RefereeRating).filter_by(booking_id=booking_id, rater_id=user.id).first():
        raise HTTPException(status_code=409, detail="Энэ захиалгад үнэлгээ өгсөн байна.")
    rating = RefereeRating(
        booking_id=booking_id, referee_user_id=item.referee_user_id,
        rater_id=user.id, score=payload.score, comment=payload.comment,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating
