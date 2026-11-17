from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserProfile
from app.schemas import UserProfileRequest, UserProfileResponse

router = APIRouter(prefix="/profile", tags=["user profile"])


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(user: User = Depends(get_current_user)):
    if user.profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профайлын мэдээлэл хараахан бүртгэгдээгүй байна.",
        )
    return user.profile


@router.put("/me", response_model=UserProfileResponse)
def save_my_profile(
    payload: UserProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    full_name = payload.full_name.strip()
    if not full_name:
        raise HTTPException(status_code=422, detail="Овог, нэрээ оруулна уу.")

    profile = user.profile
    if profile is None:
        profile = UserProfile(user_id=user.id, full_name=full_name)
        db.add(profile)

    profile.full_name = full_name
    profile.sport = payload.sport
    profile.region = payload.region
    db.commit()
    db.refresh(profile)
    return profile
