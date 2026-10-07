from datetime import datetime


from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.base import utcnow


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("character_a_id", "character_b_id", name="uq_conversation_pair"),)

    id: int | None = Field(default=None, primary_key=True)
    character_a_id: int = Field(index=True, foreign_key="characters.id")
    character_b_id: int = Field(index=True, foreign_key="characters.id")
    last_message_at: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)


class ConversationSession(SQLModel, table=True):
    __tablename__ = "conversation_sessions"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(index=True, foreign_key="conversations.id")
    status: str = Field(default="ACTIVE", index=True, max_length=16)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = Field(default=None)
    ended_reason: str | None = Field(default=None, max_length=200)


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(index=True, foreign_key="conversations.id")
    session_id: int | None = Field(default=None, index=True, foreign_key="conversation_sessions.id")
    sender_character_id: int = Field(index=True, foreign_key="characters.id")
    content: str = Field(max_length=5000)
    created_at: datetime = Field(default_factory=utcnow, index=True)
