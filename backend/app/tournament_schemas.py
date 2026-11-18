from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class TournamentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    sport: str = Field(min_length=2, max_length=80)
    format: str = Field(default="single_elimination", pattern="^(single_elimination|round_robin)$")
    region: str = Field(min_length=2, max_length=120)
    venue: str = Field(min_length=2, max_length=200)
    starts_at: datetime
    registration_deadline: datetime | None = None
    max_participants: int = Field(default=64, ge=2, le=2048)
    age_group: str | None = Field(default=None, max_length=80)
    weight_class: str | None = Field(default=None, max_length=80)
    rules: str | None = Field(default=None, max_length=5000)

    @field_validator("title", "sport", "region", "venue", "age_group", "weight_class", "rules")
    @classmethod
    def clean_text(cls, value):
        return value.strip() if value else value


class TournamentOutput(BaseModel):
    id: int
    organizer_id: int
    title: str
    sport: str
    format: str
    region: str
    venue: str
    starts_at: datetime
    registration_deadline: datetime | None
    max_participants: int
    age_group: str | None
    weight_class: str | None
    rules: str | None
    status: str
    participant_count: int
    created_at: datetime


class ParticipantCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    club_name: str | None = Field(default=None, max_length=120)
    contact_phone: str = Field(min_length=8, max_length=24)
    seed: int = Field(default=0, ge=0, le=2048)

    @field_validator("full_name", "club_name", "contact_phone")
    @classmethod
    def clean_text(cls, value):
        return value.strip() if value else value


class ParticipantOutput(BaseModel):
    # Public participant responses intentionally exclude account IDs and phone numbers.
    id: int
    tournament_id: int
    full_name: str
    club_name: str | None
    seed: int
    status: str
    created_at: datetime


class MatchScoreInput(BaseModel):
    score1: int = Field(ge=0, le=999)
    score2: int = Field(ge=0, le=999)
    scheduled_at: datetime | None = None
    mat_name: str | None = Field(default=None, max_length=80)


class MatchOutput(BaseModel):
    id: int
    tournament_id: int
    round_number: int
    match_number: int
    stage_name: str
    participant1_id: int | None
    participant1_name: str | None
    participant2_id: int | None
    participant2_name: str | None
    winner_id: int | None
    score1: int | None
    score2: int | None
    status: str
    scheduled_at: datetime | None
    mat_name: str | None
    next_match_id: int | None
