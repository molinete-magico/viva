from datetime import datetime


from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=4000)
    # Legacy field kept nullable for database compatibility; activities no longer depend on locations.
    location_id: int | None = Field(default=None, index=True, foreign_key="locations.id")
    host_character_id: int | None = Field(default=None, index=True, foreign_key="characters.id")
    created_by: str = Field(default="system", max_length=16)
    # Legacy column retained for old databases, but activities are immediate roleplay situations.
    scheduled_at: datetime | None = Field(default=None, index=True)
    status: str = Field(default="OPEN", index=True, max_length=16)
    kind: str = Field(default="social", max_length=32)
    max_participants: int | None = Field(default=None)
    cancel_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utcnow, index=True)


class EventParticipant(SQLModel, table=True):
    __tablename__ = "event_participants"
    __table_args__ = (UniqueConstraint("event_id", "character_id", name="uq_event_participant"),)

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(index=True, foreign_key="events.id")
    character_id: int = Field(index=True, foreign_key="characters.id")
    status: str = Field(default="INVITED", max_length=16)
    responded_at: datetime | None = Field(default=None)
    joined_at: datetime | None = Field(default=None)


class EventSession(SQLModel, table=True):
    __tablename__ = "event_sessions"
    __table_args__ = (UniqueConstraint("event_id", "player_character_id", name="uq_event_session"),)

    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(index=True, foreign_key="events.id")
    player_character_id: int = Field(index=True, foreign_key="characters.id")
    status: str = Field(default="ACTIVE", index=True, max_length=16)
    turn_count: int = Field(default=0)
    last_activity_at: datetime = Field(default_factory=utcnow, index=True)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = Field(default=None)
    resume_count: int = Field(default=0)
    outcome_id: int | None = Field(default=None)


class EventTurn(SQLModel, table=True):
    __tablename__ = "event_turns"
    __table_args__ = (UniqueConstraint("session_id", "turn_index", name="uq_event_turn"),)

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, foreign_key="event_sessions.id")
    turn_index: int = Field(default=0)
    narrative: str = Field(default="", max_length=8000)
    dialogue: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    available_actions: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    player_action_id: str | None = Field(default=None, max_length=64)
    player_action_label: str | None = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=utcnow)


class EventOutcome(SQLModel, table=True):
    __tablename__ = "event_outcomes"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(index=True, unique=True, foreign_key="event_sessions.id")
    summary: str = Field(default="", max_length=4000)
    relationship_changes: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    memories: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    social_effects: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    future_hooks: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    applied_at: datetime = Field(default_factory=utcnow)


class FutureHook(SQLModel, table=True):
    __tablename__ = "future_hooks"

    id: int | None = Field(default=None, primary_key=True)
    source_type: str = Field(max_length=8)
    source_id: int | None = Field(default=None)
    target_character_id: int = Field(index=True, foreign_key="characters.id")
    kind: str = Field(max_length=32)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    due_at: datetime | None = Field(default=None, index=True)
    status: str = Field(default="PENDING", index=True, max_length=16)
    created_at: datetime = Field(default_factory=utcnow)
