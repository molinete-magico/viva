from datetime import date, datetime

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class District(SQLModel, table=True):
    __tablename__ = "districts"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=120)
    slug: str = Field(index=True, unique=True, max_length=120)
    description: str = Field(default="", max_length=2000)
    sort_order: int = Field(default=0)


class Location(SQLModel, table=True):
    __tablename__ = "locations"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=120)
    slug: str = Field(index=True, unique=True, max_length=120)
    district_id: int = Field(index=True, foreign_key="districts.id")
    kind: str = Field(default="shop", max_length=32)
    description: str = Field(default="", max_length=2000)
    opening_hours: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    activities: list | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    is_public: bool = Field(default=True)


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True, unique=True, max_length=120)
    description: str = Field(default="", max_length=2000)
    employer_location_id: int | None = Field(default=None, index=True, foreign_key="locations.id")
    salary_per_shift: float = Field(default=0)
    schedule_template: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))


class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"

    id: int | None = Field(default=None, primary_key=True)
    character_id: int = Field(index=True, foreign_key="characters.id")
    day_of_week: int | None = Field(default=None)
    start_time: str = Field(default="09:00", max_length=5)
    end_time: str = Field(default="18:00", max_length=5)
    activity: str = Field(default="", max_length=200)
    location_id: int | None = Field(default=None, index=True, foreign_key="locations.id")


class WorldState(SQLModel, table=True):
    __tablename__ = "world_state"

    id: int | None = Field(default=1, primary_key=True)
    current_date: date = Field(index=True)
    current_time: str = Field(default="08:00", max_length=5)
    last_simulated_at: datetime = Field(default_factory=utcnow, index=True)
    last_catchup_at: datetime | None = Field(default=None)
    city_name: str = Field(default="Vila Serena", max_length=120)


class SimulationLog(SQLModel, table=True):
    __tablename__ = "simulation_logs"

    id: int | None = Field(default=None, primary_key=True)
    ran_at: datetime = Field(default_factory=utcnow, index=True)
    kind: str = Field(default="manual", max_length=32)
    elapsed_minutes: int = Field(default=0)
    summary: str = Field(default="", max_length=2000)
    payload: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
