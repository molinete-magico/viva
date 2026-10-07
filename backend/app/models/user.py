from datetime import datetime


from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    password_hash: str = Field(max_length=255)
    is_admin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    active_character_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)
