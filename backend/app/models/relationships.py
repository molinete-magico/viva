from datetime import datetime


from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class Relationship(SQLModel, table=True):
    __tablename__ = "relationships"
    __table_args__ = (UniqueConstraint("character_a_id", "character_b_id", name="uq_relationship_pair"),)

    id: int | None = Field(default=None, primary_key=True)
    character_a_id: int = Field(index=True, foreign_key="characters.id")
    character_b_id: int = Field(index=True, foreign_key="characters.id")
    familiarity: int = Field(default=0)
    friendship: int = Field(default=0)
    trust: int = Field(default=0)
    romance: int = Field(default=0)
    respect: int = Field(default=0)
    tension: int = Field(default=0)
    last_interaction_at: datetime | None = Field(default=None, index=True)
    updated_at: datetime = Field(default_factory=utcnow)


class Memory(SQLModel, table=True):
    __tablename__ = "memories"

    id: int | None = Field(default=None, primary_key=True)
    owner_character_id: int = Field(index=True, foreign_key="characters.id")
    other_character_id: int | None = Field(default=None, index=True, foreign_key="characters.id")
    category: str = Field(default="NORMAL", index=True, max_length=16)
    kind: str = Field(default="shared_experience", max_length=40)
    content: str = Field(max_length=4000)
    context: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    occurred_at: datetime = Field(default_factory=utcnow, index=True)
    importance: int = Field(default=50)
    source_event_id: int | None = Field(default=None, index=True, foreign_key="events.id")
    dedupe_key: str | None = Field(default=None, index=True, max_length=200)
    created_at: datetime = Field(default_factory=utcnow)
