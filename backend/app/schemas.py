from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = "".join(ch for ch in value.strip() if ch not in " -()")
        if normalized.startswith("00"):
            normalized = "+" + normalized[2:]
        has_prefix = normalized.startswith("+")
        digits = normalized[1:] if has_prefix else normalized
        if not digits.isdigit() or not 8 <= len(digits) <= 15:
            raise ValueError("Утасны дугаараа зөв оруулна уу.")
        if not has_prefix and len(digits) == 8:
            return "+976" + digits
        if not has_prefix and len(digits) == 11 and digits.startswith("976"):
            return "+" + digits
        return normalized


class LoginRequest(RegisterRequest):
    pass


class UserResponse(BaseModel):
    id: int
    phone: str
    roles: list[str]
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class UserProfileRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    sport: str | None = Field(default=None, max_length=60)
    region: str | None = Field(default=None, max_length=120)

    @field_validator("full_name", "sport", "region")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class UserProfileResponse(BaseModel):
    full_name: str
    sport: str | None
    region: str | None
    updated_at: datetime
