import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserRole
from app.referee_models import RefereeProfile

router = APIRouter(prefix="/admin", tags=["admin"])


class BootstrapRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class RefereeAccessRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    sport: str = Field(min_length=2, max_length=80)
    rank: str = Field(min_length=1, max_length=80)
    region: str = Field(min_length=2, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    base_fee: int = Field(default=0, ge=0, le=100_000_000)


class VerificationRequest(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=1000)


def _is_admin(user: User) -> bool:
    return any(role.role == "admin" for role in user.roles)


@router.post("/bootstrap", status_code=200)
def bootstrap_first_admin(
    payload: BootstrapRequest,
    x_admin_bootstrap_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    # One-time owner bootstrap. Disable the key after creating the first admin.
    settings = get_settings()
    expected = settings.admin_bootstrap_key
    if not expected or not x_admin_bootstrap_key or not hmac.compare_digest(expected, x_admin_bootstrap_key):
        raise HTTPException(status_code=403, detail="Админ үүсгэх түлхүүр буруу эсвэл тохируулаагүй.")
    if db.query(UserRole).filter(UserRole.role == "admin").first():
        raise HTTPException(status_code=409, detail="Админ эрх аль хэдийн үүссэн байна.")
    user = db.query(User).filter(User.phone == payload.phone).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Эхлээд энэ утсаар хэрэглэгч бүртгүүлнэ үү.")
    user.roles.append(UserRole(role="admin"))
    db.commit()
    return {"status": "admin_created", "user_id": user.id, "instruction": "ADMIN_BOOTSTRAP_KEY-г серверийн тохиргооноос устгана уу."}


@router.post("/referees/grant", status_code=201)
def grant_referee_access(
    payload: RefereeAccessRequest,
    admin: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(admin):
        raise HTTPException(status_code=403, detail="Зөвхөн админ энэ үйлдлийг хийнэ.")
    user = db.query(User).filter(User.phone == payload.phone).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Хэрэглэгч олдсонгүй.")
    if not any(role.role == "referee" for role in user.roles):
        user.roles.append(UserRole(role="referee"))
    profile = db.query(RefereeProfile).filter(RefereeProfile.user_id == user.id).first()
    values = payload.model_dump(exclude={"phone"})
    if profile is None:
        profile = RefereeProfile(user_id=user.id, **values, verification_status="pending")
        db.add(profile)
    else:
        for key, value in values.items():
            setattr(profile, key, value)
        profile.verification_status = "pending"
    db.commit()
    return {"status": "referee_role_granted", "user_id": user.id, "verification_status": "pending"}


@router.post("/referees/{user_id}/verify")
def verify_referee(
    user_id: int,
    payload: VerificationRequest,
    admin: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_admin(admin):
        raise HTTPException(status_code=403, detail="Зөвхөн админ лиценз баталгаажуулна.")
    profile = db.query(RefereeProfile).filter(RefereeProfile.user_id == user_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Шүүгчийн профайл олдсонгүй.")
    profile.verification_status = "verified" if payload.approved else "rejected"
    db.commit()
    return {
        "user_id": user_id,
        "verification_status": profile.verification_status,
        "note": payload.note,
    }
