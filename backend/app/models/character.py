from datetime import datetime


from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class Character(SQLModel, table=True):
    __tablename__ = "characters"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, index=True, foreign_key="users.id")
    name: str = Field(index=True, max_length=120)
    age: int = Field(default=20)
    pronouns: str = Field(default="", max_length=60)
    bio: str = Field(default="", max_length=2000)
    profession_label: str = Field(default="", max_length=120)
    is_npc: bool = Field(default=False, index=True)
    personality: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    communication_style: str = Field(default="neutra", max_length=60)
    hobbies: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    likes: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    dislikes: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    goals: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    flaws: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    favorite_location_ids: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    money: float = Field(default=0)
    discovered_level: int = Field(default=1)
    photo_id: int | None = Field(default=None, index=True)
    current_location_id: int | None = Field(default=None, index=True, foreign_key="locations.id")
    created_at: datetime = Field(default_factory=utcnow, index=True)


class CharacterPhoto(SQLModel, table=True):
    __tablename__ = "character_photos"

    id: int | None = Field(default=None, primary_key=True)
    character_id: int = Field(index=True, foreign_key="characters.id")
    source: str = Field(default="seed", max_length=16)
    path: str = Field(default="", max_length=500)
    label: str = Field(default="", max_length=120)
    is_primary: bool = Field(default=False)


class CharacterJob(SQLModel, table=True):
    __tablename__ = "character_jobs"

    id: int | None = Field(default=None, primary_key=True)
    character_id: int = Field(index=True, foreign_key="characters.id")
    job_id: int = Field(index=True, foreign_key="jobs.id")
    is_primary: bool = Field(default=True)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = Field(default=None)
