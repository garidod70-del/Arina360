from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


ServiceCategory = Literal[
    "coach",
    "sports_doctor",
    "strength_specialist",
    "sports_psychologist",
    "sports_nutritionist",
    "physiotherapist",
    "sports_analyst",
    "venue_booking",
    "sports_store",
    "clubs_training",
]


class ServiceProviderInput(BaseModel):
    category: ServiceCategory
    display_name: str = Field(min_length=2, max_length=140)
    description: str = Field(min_length=10, max_length=4000)
    sport: str | None = Field(default=None, max_length=80)
    region: str = Field(min_length=2, max_length=120)
    price_from: int = Field(default=0, ge=0, le=1_000_000_000)
    credentials: str | None = Field(default=None, max_length=240)

    @field_validator("display_name", "description", "sport", "region", "credentials")
    @classmethod
    def clean_text(cls, value):
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ServiceProviderOutput(BaseModel):
    id: int
    user_id: int
    category: str
    display_name: str
    description: str
    sport: str | None
    region: str
    price_from: int
    credentials: str | None
    verification_status: str
    verified_at: datetime | None
    created_at: datetime


class ServiceRequestInput(BaseModel):
    category: ServiceCategory
    provider_user_id: int | None = None
    title: str = Field(min_length=3, max_length=160)
    details: str = Field(min_length=5, max_length=4000)
    sport: str | None = Field(default=None, max_length=80)
    region: str = Field(min_length=2, max_length=120)
    preferred_at: datetime | None = None
    contact_phone: str = Field(min_length=8, max_length=24)

    @field_validator("title", "details", "sport", "region", "contact_phone")
    @classmethod
    def clean_text(cls, value):
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ServiceRequestResponse(BaseModel):
    id: int
    requester_id: int
    provider_user_id: int | None
    category: str
    title: str
    details: str
    sport: str | None
    region: str
    preferred_at: datetime | None
    contact_phone: str
    status: str
    payment_status: str = "unpaid"
    response_note: str | None
    created_at: datetime
    updated_at: datetime


class ServiceRequestDecision(BaseModel):
    accepted: bool
    note: str | None = Field(default=None, max_length=2000)


class ServiceVerificationInput(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=2000)
