from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.database.session import get_session
from app.domain.errors import ServiceError
from app.llm import LLMError
from app.models import Character, Conversation, User
from app.schemas.common import Listing
from app.schemas.messaging import (
    ConversationDetailOut,
    ConversationOut,
    EndSessionOut,
    MessageList,
    MessageOut,
    SendMessageRequest,
    SendMessageResponse,
    message_out,
    serialize_conversation,
)
from app.services import character_service, messaging_service

router = APIRouter(prefix="/conversations", tags=["messages"])


@router.get("", response_model=Listing[ConversationOut])
def list_conversations(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user.active_character_id is None:
        return Listing(items=[])
    viewer_id = user.active_character_id
    conversations = session.exec(
        select(Conversation)
        .where(
            or_(
                Conversation.character_a_id == viewer_id,
                Conversation.character_b_id == viewer_id,
            )
        )
        .order_by(Conversation.last_message_at.desc().nullslast())
        .limit(100)
    ).all()
    items = [serialize_conversation(session, c, viewer_id) for c in conversations]
    return Listing(items=items)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    conversation = messaging_service.conversation_for_character(session, conversation_id, character.id)
    return messaging_service.serialize_conversation_detail(session, conversation, character.id)


@router.get("/{conversation_id}/messages", response_model=MessageList)
def list_messages(
    conversation_id: int,
    before_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    conversation = messaging_service.conversation_for_character(session, conversation_id, character.id)
    messages = messaging_service.messages_for(session, conversation, before_id=before_id, limit=limit)
    return MessageList(items=[message_out(m, character.id) for m in messages])


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message(
    conversation_id: int,
    req: SendMessageRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    conversation = messaging_service.conversation_for_character(session, conversation_id, character.id)
    try:
        sent, reply, warning = messaging_service.send_with_npc_reply(session, conversation, character, req.content)
    except LLMError as exc:
        raise ServiceError(
            f"{exc}. Sua mensagem foi enviada; tente novamente em instantes.",
            503,
        ) from exc
    return SendMessageResponse(
        message=message_out(sent, character.id),
        npc_reply=message_out(reply, character.id) if reply is not None else None,
        warning=warning,
    )


@router.post("/{conversation_id}/end-session", response_model=EndSessionOut)
def end_session(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    conversation = messaging_service.conversation_for_character(session, conversation_id, character.id)
    messaging_service.end_active_session(session, conversation)
    return EndSessionOut(ok=True)