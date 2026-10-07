from datetime import datetime


from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: int | None = Field(default=None, primary_key=True)
    author_character_id: int = Field(index=True, foreign_key="characters.id")
    content: str = Field(max_length=5000)
    kind: str = Field(default="post", max_length=16)
    location_id: int | None = Field(default=None, index=True, foreign_key="locations.id")
    event_id: int | None = Field(default=None, index=True, foreign_key="events.id")
    created_at: datetime = Field(default_factory=utcnow, index=True)


class Comment(SQLModel, table=True):
    __tablename__ = "comments"

    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(index=True, foreign_key="posts.id")
    author_character_id: int = Field(index=True, foreign_key="characters.id")
    content: str = Field(max_length=2000)
    parent_comment_id: int | None = Field(default=None, foreign_key="comments.id")
    created_at: datetime = Field(default_factory=utcnow, index=True)


class Like(SQLModel, table=True):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("target_type", "target_id", "character_id", name="uq_like_target"),)

    id: int | None = Field(default=None, primary_key=True)
    target_type: str = Field(index=True, max_length=16)
    target_id: int = Field(index=True)
    character_id: int = Field(index=True, foreign_key="characters.id")
    created_at: datetime = Field(default_factory=utcnow)


class Follow(SQLModel, table=True):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_character_id", "followed_character_id", name="uq_follow_pair"),)

    id: int | None = Field(default=None, primary_key=True)
    follower_character_id: int = Field(index=True, foreign_key="characters.id")
    followed_character_id: int = Field(index=True, foreign_key="characters.id")
    created_at: datetime = Field(default_factory=utcnow)


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: int | None = Field(default=None, primary_key=True)
    character_id: int = Field(index=True, foreign_key="characters.id")
    type: str = Field(index=True, max_length=40)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utcnow, index=True)
    read_at: datetime | None = Field(default=None)
