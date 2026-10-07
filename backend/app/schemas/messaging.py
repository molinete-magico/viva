from datetime import datetime

from pydantic import BaseModel, Field

from sqlmodel import Session, select

from app.models import Character, Conversation, Message
from app.schemas.social import AuthorBrief, author_brief
from app.services.character_service import photo_url_map


class ConversationOut(BaseModel):
    id: int
    partner: AuthorBrief
    last_message_at: datetime | None = None
    last_message_preview: str | None = None


class ConversationDetailOut(ConversationOut):
    active_session_id: int | None = None


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    sender_character_id: int
    content: str
    created_at: datetime
    is_mine: bool = False


class MessageList(BaseModel):
    items: list[MessageOut]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class SendMessageResponse(BaseModel):
    message: MessageOut
    npc_reply: MessageOut | None = None
    warning: str | None = None


class EndSessionOut(BaseModel):
    ok: bool = True


def message_out(message: Message, viewer_id: int) -> MessageOut:
    return MessageOut(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_character_id=message.sender_character_id,
        content=message.content,
        created_at=message.created_at,
        is_mine=message.sender_character_id == viewer_id,
    )


def serialize_conversation(session: Session, conversation: Conversation, viewer_id: int) -> ConversationOut:
    partner_id = (
        conversation.character_b_id
        if conversation.character_a_id == viewer_id
        else conversation.character_a_id
    )
    partner = session.get(Character, partner_id)
    if partner is None:
        raise ValueError("parceiro ausente")
    photos = photo_url_map(session, [partner])
    last = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
        .limit(1)
    ).first()
    return ConversationOut(
        id=conversation.id,
        partner=author_brief(partner, photo_url=photos.get(partner.id)),
        last_message_at=conversation.last_message_at,
        last_message_preview=last.content[:120] if last else None,
    )