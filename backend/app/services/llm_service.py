"""Geração de conteúdo público dos NPCs."""

import asyncio
from datetime import datetime, time, timezone

from sqlmodel import Session, select

from app.llm import LLMError, get_provider
from app.llm.prompts import build_comment_prompt, build_post_prompt, complete_with_timeout
from app.models import Character, Follow, Memory, Post, WorldState


def generate_npc_post(session: Session, npc: Character, *, simulated_at: datetime | None = None, extra_context: str = "") -> Post:
    """Gera um post público do NPC usando o modelo rápido.

    Levanta LLMError se a API falhar; o chamador decide o que fazer.
    """
    world = session.get(WorldState, 1)
    world_payload = {
        "date": world.current_date.isoformat() if world else "",
        "time": world.current_time if world else "08:00",
        "day_name": _weekday(world.current_date.weekday()) if world else "",
    }
    recent_memories = session.exec(
        select(Memory)
        .where(
            Memory.owner_character_id == npc.id,
            Memory.occurred_at.is_not(None),
        )
        .order_by(Memory.occurred_at.desc())
        .limit(6)
    ).all()
    recent_posts = session.exec(
        select(Post)
        .where(Post.author_character_id == npc.id)
        .order_by(Post.created_at.desc())
        .limit(3)
    ).all()
    context_lines: list[str] = []
    for memory in recent_memories:
        other = session.get(Character, memory.other_character_id) if memory.other_character_id else None
        subject = f" com {other.name}" if other else ""
        context_lines.append(f"Memória recente{subject}: {memory.content}")
    for previous in recent_posts:
        context_lines.append(f"Post recente: {previous.content}")
    recent_context = "\n".join(context_lines[:9])
    if extra_context.strip():
        recent_context = (recent_context + "\n" + extra_context.strip()).strip()

    system_prompt, user_prompt = build_post_prompt(
        npc_name=npc.name,
        npc_role=npc.profession_label or "morador(a) da Vila Serena",
        npc_personality=npc.personality,
        npc_hobbies=npc.hobbies,
        world=world_payload,
        recent_context=recent_context,
    )
    text = asyncio.run(
        complete_with_timeout(
            get_provider(),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            personality=npc.personality,
            model="quick",
        )
    )
    if not text.strip():
        raise LLMError("O provedor respondeu vazio para o post.")
    post_time = simulated_at or (datetime.combine(world.current_date, time.fromisoformat(world.current_time), tzinfo=timezone.utc) if world else datetime.now(timezone.utc))
    post = Post(author_character_id=npc.id, content=text.strip(), kind="post", created_at=post_time)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


def generate_posts_for_active_npcs(session: Session, day: str) -> int:
    """Publica um post por NPC com seguidores que ainda não postou hoje.

    Erros de LLM (limite/indisponibilidade) são ignorados para o avanço
    do mundo não quebrar; retorna quantos posts foram criados.
    """
    npc_ids = list(
        session.exec(select(Follow.followed_character_id).distinct()).all()
    )
    if not npc_ids:
        return 0
    npcs = session.exec(
        select(Character).where(Character.id.in_(npc_ids), Character.is_npc.is_(True))
    ).all()
    created = 0
    for npc in npcs:
        already = session.exec(
            select(Post)
            .where(Post.author_character_id == npc.id)
            .order_by(Post.id.desc())
            .limit(1)
        ).first()
        if already is not None and already.created_at.date().isoformat() >= day:
            continue
        try:
            generate_npc_post(session, npc)
        except LLMError:
            continue
        created += 1
    return created


_WEEKDAYS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _weekday(weekday: int) -> str:
    return _WEEKDAYS[weekday]


def generate_npc_comment(session: Session, npc: Character, post: Post) -> str:
    """Gera um comentário curto do NPC para o post de um morador (modelo quick).

    Levanta LLMError se o provedor falhar; se a resposta vier vazia, retorna "".
    """
    world = session.get(WorldState, 1)
    world_payload = {
        "date": world.current_date.isoformat() if world else "",
        "time": world.current_time if world else "08:00",
        "day_name": _weekday(world.current_date.weekday()) if world else "",
    }
    system_prompt, user_prompt = build_comment_prompt(
        npc_name=npc.name,
        npc_personality=npc.personality,
        post_content=post.content,
        post_author=_author_name(session, post),
        world=world_payload,
    )
    text = asyncio.run(
        complete_with_timeout(
            get_provider(),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            personality=npc.personality,
            model="quick",
        )
    )
    if not text.strip():
        raise LLMError("O provedor respondeu vazio para o comentário.")
    return text.strip()


def _author_name(session: Session, post: Post) -> str:
    author = session.get(Character, post.author_character_id)
    return author.name if author is not None else "um morador"