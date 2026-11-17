from datetime import date, time, datetime
from pydantic import BaseModel, Field, field_validator


class VenueSlotInput(BaseModel):
    venue_name: str = Field(min_length=2, max_length=160)
    venue_address: str = Field(min_length=3, max_length=240)
    sport: str = Field(min_length=2, max_length=80)
    booking_date: date
    start_time: time
    end_time: time
    price: int = Field(default=0, ge=0, le=1_000_000_000)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("venue_name", "venue_address", "sport", "notes")
    @classmethod
    def clean_text(cls, value):
        return value.strip() if value else value


class VenueSlotOutput(BaseModel):
    id: int
    provider_user_id: int
    venue_name: str
    venue_address: str
    sport: str
    booking_date: date
    start_time: time
    end_time: time
    price: int
    notes: str | None
    status: str


class VenueBookingInput(BaseModel):
    contact_phone: str = Field(min_length=8, max_length=24)
    purpose: str | None = Field(default=None, max_length=500)

    @field_validator("contact_phone", "purpose")
    @classmethod
    def clean_text(cls, value):
        return value.strip() if value else value


class VenueBookingOutput(BaseModel):
    id: int
    slot_id: int
    customer_id: int
    provider_user_id: int
    contact_phone: str
    purpose: str | None
    status: str
    created_at: datetime


class VenueBookingDecision(BaseModel):
    accepted: bool
    note: str | None = Field(default=None, max_length=500)
