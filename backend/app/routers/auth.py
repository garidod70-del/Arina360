from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserRole
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])


def _auth_response(user: User) -> AuthResponse:
    settings = get_settings()
    return AuthResponse(
        access_token=create_access_token(str(user.id)),
        expires_in=settings.jwt_expire_minutes * 60,
        user=UserResponse(
            id=user.id,
            phone=user.phone,
            roles=[item.role for item in user.roles],
            created_at=user.created_at,
        ),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(status_code=409, detail="Энэ утасны дугаар бүртгэлтэй байна.")
    user = User(phone=payload.phone, password_hash=hash_password(payload.password))
    user.roles.append(UserRole(role="athlete"))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Энэ утасны дугаар бүртгэлтэй байна.")
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == payload.phone).first()
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Утасны дугаар эсвэл нууц үг буруу байна.")
    return _auth_response(user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        phone=user.phone,
        roles=[item.role for item in user.roles],
        created_at=user.created_at,
    )
