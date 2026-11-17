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
        digits = normalized[1:] if normalized.startswith("+") else normalized
        if not digits.isdigit() or not 8 <= len(digits) <= 15:
            raise ValueError("Утасны дугаараа зөв оруулна уу.")
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
