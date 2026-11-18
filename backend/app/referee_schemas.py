from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class RefereeProfileInput(BaseModel):
    sport: str = Field(min_length=2, max_length=80)
    rank: str = Field(min_length=1, max_length=80)
    region: str = Field(min_length=2, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    base_fee: int = Field(default=0, ge=0, le=100_000_000)


class RefereeProfileOutput(BaseModel):
    user_id: int
    full_name: str | None
    sport: str
    rank: str
    region: str
    bio: str | None
    base_fee: int
    license_number: str | None = None
    license_issuer: str | None = None
    license_expires_at: datetime | None = None
    verification_status: str
    verified_at: datetime | None = None
    average_rating: float | None = None
    rating_count: int = 0


class RefereeBookingInput(BaseModel):
    sport: str = Field(min_length=2, max_length=80)
    rank: str = Field(min_length=1, max_length=80)
    booking_type: str = Field(min_length=2, max_length=100)
    event_at: datetime
    venue: str = Field(min_length=2, max_length=240)
    referee_count: int = Field(ge=1, le=100)
    payment_type: str = Field(min_length=2, max_length=40)
    unit_fee: int = Field(ge=0, le=100_000_000)
    work_days: int = Field(default=1, ge=1, le=365)
    transport_fee: int = Field(default=0, ge=0, le=100_000_000)
    food_fee: int = Field(default=0, ge=0, le=100_000_000)
    contact_name: str = Field(min_length=2, max_length=120)
    contact_phone: str | None = Field(default=None, min_length=8, max_length=24)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("event_at")
    @classmethod
    def event_must_be_future(cls, value: datetime) -> datetime:
        from datetime import timezone
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        if value <= datetime.now(timezone.utc):
            raise ValueError("Тэмцээний огноо ирээдүйд байх ёстой.")
        return value


class RefereeBookingOutput(BaseModel):
    id: int
    requester_id: int
    referee_user_id: int | None
    sport: str
    rank: str
    booking_type: str
    event_at: datetime
    venue: str
    referee_count: int
    payment_type: str
    unit_fee: int
    work_days: int
    transport_fee: int
    food_fee: int
    total_amount: int
    contact_name: str
    contact_phone: str
    notes: str | None
    status: str
    payment_status: str = "unpaid"
    created_at: datetime


class RefereeRatingInput(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class RefereeRatingOutput(BaseModel):
    id: int
    booking_id: int
    referee_user_id: int
    rater_id: int
    score: int
    comment: str | None
    created_at: datetime
