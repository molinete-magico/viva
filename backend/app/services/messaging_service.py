from datetime import timedelta

from sqlmodel import Session, select

from app.domain.errors import ServiceError
from app.llm import LLMError, RateLimitError, get_provider
from app.llm.prompts import build_dialogue_prompt, complete_with_timeout
from app.models import Character, Conversation, ConversationSession, Message, Notification, WorldState
from app.models.base import utcnow
from app.schemas.messaging import (
    ConversationDetailOut,
    ConversationOut,
    MessageOut,
    message_out,
    serialize_conversation,
)

WEEKDAYS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def get_conversation(session: Session, conversation_id: int) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise ServiceError("Conversa não encontrada.", 404)
    return conversation


def get_or_create_conversation(session: Session, player: Character, npc: Character) -> Conversation:
    if not npc.is_npc:
        raise ServiceError("Por enquanto só dá para conversar com moradores da cidade.", 400)
    if npc.id == player.id:
        raise ServiceError("Você não pode conversar consigo mesmo.", 400)
    a, b = (min(player.id, npc.id), max(player.id, npc.id))
    conversation = session.exec(
        select(Conversation).where(Conversation.character_a_id == a, Conversation.character_b_id == b)
    ).first()
    if conversation is None:
        conversation = Conversation(character_a_id=a, character_b_id=b)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
    return conversation


def conversation_for_character(session: Session, conversation_id: int, character_id: int) -> Conversation:
    conversation = get_conversation(session, conversation_id)
    if character_id not in (conversation.character_a_id, conversation.character_b_id):
        raise ServiceError("Você não participa dessa conversa.", 403)
    return conversation


def ensure_active_session(session: Session, conversation: Conversation) -> ConversationSession:
    active = session.exec(
        select(ConversationSession).where(
            ConversationSession.conversation_id == conversation.id,
            ConversationSession.status == "ACTIVE",
        )
    ).first()
    if active is not None:
        return active
    for stale in session.exec(
        select(ConversationSession).where(
            ConversationSession.conversation_id == conversation.id,
            ConversationSession.status.in_(["ACTIVE", "IDLE"]),
        )
    ).all():
        stale.status = "ENDED"
        stale.ended_reason = "session_replaced"
        stale.ended_at = utcnow()
        session.add(stale)
    new_session = ConversationSession(conversation_id=conversation.id, status="ACTIVE")
    session.add(new_session)
    session.commit()
    session.refresh(new_session)
    return new_session


def end_active_session(session: Session, conversation: Conversation, reason: str = "user_end") -> None:
    for active in session.exec(
        select(ConversationSession).where(
            ConversationSession.conversation_id == conversation.id,
            ConversationSession.status.in_(["ACTIVE", "IDLE"]),
        )
    ).all():
        active.status = "ENDED"
        active.ended_reason = reason
        active.ended_at = utcnow()
        session.add(active)
    session.commit()


def idle_conversation_sessions(session: Session, *, idle_minutes: int = 60) -> int:
    """Conversas sem mensagem recente passam para IDLE (guarda o histórico).

    ACTIVE ⇄ IDLE: ao escrever de novo, uma sessão nova ACTIVE começa e as
    anteriores terminam (session_replaced). Rodado no catch-up.
    """
    cutoff = utcnow() - timedelta(minutes=idle_minutes)
    changed = 0
    for conversation_session in session.exec(
        select(ConversationSession).where(ConversationSession.status == "ACTIVE")
    ).all():
        conversation = session.get(Conversation, conversation_session.conversation_id)
        last = conversation.last_message_at if conversation else None
        if last is not None and last < cutoff:
            conversation_session.status = "IDLE"
            session.add(conversation_session)
            changed += 1
    if changed:
        session.commit()
    return changed


def messages_for(
    session: Session,
    conversation: Conversation,
    before_id: int | None = None,
    limit: int = 50,
) -> list[Message]:
    query = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
    )
    if before_id is not None:
        query = query.where(Message.id < before_id)
    rows = session.exec(query.limit(limit)).all()
    return list(reversed(rows))


def serialize_conversation_detail(session: Session, conversation: Conversation, viewer_id: int) -> ConversationDetailOut:
    out = serialize_conversation(session, conversation, viewer_id)
    active = session.exec(
        select(ConversationSession).where(
            ConversationSession.conversation_id == conversation.id,
            ConversationSession.status == "ACTIVE",
        )
    ).first()
    return ConversationDetailOut(**out.model_dump(), active_session_id=active.id if active else None)


def send_with_npc_reply(
    session: Session,
    conversation: Conversation,
    sender: Character,
    content: str,
) -> tuple[Message, Message | None, str | None]:
    content = content.strip()
    if not content:
        raise ServiceError("A mensagem não pode ficar vazia.", 400)
    if sender.id not in (conversation.character_a_id, conversation.character_b_id):
        raise ServiceError("Você não participa dessa conversa.", 403)

    partner_id = (
        conversation.character_b_id
        if conversation.character_a_id == sender.id
        else conversation.character_a_id
    )
    partner = session.get(Character, partner_id)
    if partner is None:
        raise ServiceError("Morador não encontrado.", 404)

    new_session = ensure_active_session(session, conversation)
    sent = Message(
        conversation_id=conversation.id,
        session_id=new_session.id,
        sender_character_id=sender.id,
        content=content,
    )
    session.add(sent)
    session.commit()
    session.refresh(sent)

    world = session.get(WorldState, 1)
    recent = messages_for(session, conversation, limit=12)
    system_prompt, user_prompt = build_dialogue_prompt(
        npc_name=partner.name,
        npc_role=partner.profession_label or "morador(a) da Vila Serena",
        npc_bio=partner.bio,
        npc_style=partner.communication_style,
        npc_personality=partner.personality,
        npc_likes=partner.likes,
        npc_dislikes=partner.dislikes,
        npc_hobbies=partner.hobbies,
        npc_goals=partner.goals,
        player_name=sender.name,
        world={
            "date": world.current_date.isoformat() if world else "",
            "time": world.current_time if world else "08:00",
            "day_name": WEEKDAYS[world.current_date.weekday()] if world else "",
        },
        recent_messages=[(sender.name if m.sender_character_id == sender.id else partner.name, m.content) for m in recent],
    )
    try:
        reply_text = provider_complete(partner, system_prompt, user_prompt)
    except RateLimitError:
        return sent, None, "O limite da API foi atingido agora. Sua mensagem chegou, mas o morador ainda não respondeu — tente de novo em instantes."
    except LLMError:
        raise
    if not reply_text.strip():
        reply_text = "Hmm, me perdi por um segundo. Pode me dizer de novo?"

    reply = Message(
        conversation_id=conversation.id,
        session_id=new_session.id,
        sender_character_id=partner.id,
        content=reply_text,
    )
    session.add(reply)
    session.commit()
    session.refresh(reply)

    conversation.last_message_at = reply.created_at
    session.add(conversation)
    session.add(
        Notification(
            character_id=sender.id,
            type="NPC_DM_INITIATIVE",
            payload={"conversation_id": conversation.id},
        )
    )
    session.commit()
    return sent, reply, None


def provider_complete(partner: Character, system_prompt: str, user_prompt: str, *, model: str | None = "quick") -> str:
    """Executa o provedor com timeout — reimporta o asyncio aqui para clareza."""
    import asyncio

    from app.llm.prompts import complete_with_timeout

    return asyncio.run(complete_with_timeout(
        get_provider(),
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        personality=partner.personality,
        model=model,
    ))