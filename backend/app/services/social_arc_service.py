"""Camada de arcos sociais, objetivos e rumores persistentes.

A simulação base cria acontecimentos. Este serviço transforma acontecimentos em
estado social que continua existindo entre uma janela e outra: relações ganham
um arco legível, objetivos pessoais avançam e rumores podem circular pela rede.
O banco continua sendo a autoridade; nada aqui depende do LLM para decidir
consequências.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models import Character, Follow, Memory, Post, Relationship
from app.services import relationship_service as rel


def relationship_arc(relationship: Relationship | None) -> str:
    if relationship is None:
        return "acquaintance"
    if relationship.romance >= 45:
        return "romance"
    if relationship.tension >= 45 and relationship.friendship < 35:
        return "rivalry"
    if relationship.friendship >= 55 and relationship.trust >= 35:
        return "friendship"
    if relationship.tension >= 25:
        return "strained"
    if relationship.friendship >= 25 or relationship.familiarity >= 20:
        return "budding_friendship"
    return "acquaintance"


def _latest_arc(
    session: Session,
    owner_id: int,
    other_id: int,
) -> str | None:
    memory = session.exec(
        select(Memory)
        .where(
            Memory.owner_character_id == owner_id,
            Memory.other_character_id == other_id,
            Memory.kind == "social_arc_state",
        )
        .order_by(Memory.occurred_at.desc())
        .limit(1)
    ).first()
    if memory is None:
        return None
    return str((memory.context or {}).get("arc") or "") or None


def _record_arc(
    session: Session,
    owner: Character,
    other: Character,
    arc: str,
    moment: datetime,
    *,
    transition_from: str | None = None,
) -> None:
    if owner.id is None or other.id is None:
        return
    rel.add_memory(
        session,
        owner_character_id=owner.id,
        other_character_id=other.id,
        content=f"Minha relação com {other.name} está em uma fase de {arc.replace('_', ' ')}.",
        kind="social_arc_state",
        importance=58 if transition_from else 42,
        context={"arc": arc, "from": transition_from, "world_time": moment.isoformat()},
        dedupe_key=f"arc-state-{owner.id}-{other.id}-{arc}",
        occurred_at=moment,
    )


def update_social_arcs(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Atualiza arcos sem criar uma nova tabela/migração."""
    characters = session.exec(select(Character)).all()
    by_id = {character.id: character for character in characters if character.id is not None}
    transitions = 0
    highlights: list[str] = []

    relationships = session.exec(select(Relationship)).all()
    for relationship in relationships:
        left = by_id.get(relationship.character_a_id)
        right = by_id.get(relationship.character_b_id)
        if left is None or right is None:
            continue
        arc = relationship_arc(relationship)
        previous = _latest_arc(session, left.id, right.id)
        if previous == arc:
            continue
        _record_arc(session, left, right, arc, moment, transition_from=previous)
        _record_arc(session, right, left, arc, moment, transition_from=previous)
        transitions += 1
        if previous is None:
            highlights.append(f"{left.name} e {right.name} começaram a se aproximar ({arc.replace('_', ' ')})")
        else:
            highlights.append(f"{left.name} e {right.name} passaram de {previous.replace('_', ' ')} para {arc.replace('_', ' ')}")

    return transitions, highlights[:8]


def _social_goal(character: Character) -> str | None:
    for goal in character.goals or []:
        text = str(goal).strip()
        lowered = text.lower()
        if any(word in lowered for word in ("amiz", "amigo", "conhec", "romanc", "relacion", "social", "popular")):
            return text
    return None


def advance_character_goals(
    session: Session,
    moment: datetime,
) -> tuple[int, list[str]]:
    """Converte objetivos sociais existentes do NPC em ações pequenas e persistentes."""
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    progress = 0
    highlights: list[str] = []

    for npc in npcs:
        if npc.id is None:
            continue
        goal = _social_goal(npc)
        if not goal:
            continue

        marker = f"goal-progress-{npc.id}-{moment.date().isoformat()}"
        if session.exec(
            select(Memory).where(
                Memory.owner_character_id == npc.id,
                Memory.dedupe_key == marker,
            )
        ).first():
            continue

        relationships = [
            item
            for item in rel.list_for_character(session, npc.id)
            if item.tension < 70
        ]
        relationships.sort(
            key=lambda item: (
                item.friendship + item.familiarity + item.trust + item.respect,
                -(item.tension),
            ),
            reverse=True,
        )
        if not relationships:
            continue

        relationship = relationships[0]
        target_id = rel.pair_other_id(relationship, npc.id)
        target = session.get(Character, target_id)
        if target is None:
            continue

        before = relationship_arc(relationship)
        rel.apply_changes(
            session,
            npc.id,
            target.id,
            {"familiarity": 1, "respect": 1},
            log=False,
        )
        rel.add_memory(
            session,
            owner_character_id=npc.id,
            other_character_id=target.id,
            content=f"Dei um pequeno passo em direção ao meu objetivo: {goal}. Pensei em {target.name}.",
            kind="goal_progress",
            importance=34,
            context={"goal": goal, "arc_before": before},
            dedupe_key=marker,
            occurred_at=moment,
        )
        progress += 1
        if len(highlights) < 5:
            highlights.append(f"{npc.name} tomou uma iniciativa ligada ao objetivo: {goal}")

    return progress, highlights


def propagate_rumors(
    session: Session,
    moment: datetime,
) -> tuple[int, list[str]]:
    """Faz rumores existentes viajarem entre pessoas, com decaimento e dedupe diário."""
    cutoff = moment - timedelta(hours=36)
    rumors = session.exec(
        select(Post)
        .where(
            Post.kind == "rumor",
            Post.created_at >= cutoff,
            Post.created_at <= moment,
        )
        .order_by(Post.created_at.desc())
        .limit(12)
    ).all()
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    propagated = 0
    highlights: list[str] = []

    for rumor in rumors[:6]:
        author = session.get(Character, rumor.author_character_id)
        if author is None:
            continue
        followers = session.exec(
            select(Follow).where(Follow.followed_character_id == author.id)
        ).all()
        candidate_ids = {row.follower_character_id for row in followers}
        candidates = [
            npc for npc in npcs
            if npc.id in candidate_ids and npc.id != author.id
        ]
        for npc in candidates[:3]:
            if npc.id is None:
                continue
            day_key = moment.date().isoformat()
            learn_key = f"rumor-heard-{rumor.id}-{npc.id}-{day_key}"
            if session.exec(
                select(Memory).where(
                    Memory.owner_character_id == npc.id,
                    Memory.dedupe_key == learn_key,
                )
            ).first():
                continue

            rel_to_author = rel.relationship_between(session, npc.id, author.id)
            confidence = 0.42
            if rel_to_author is not None:
                confidence += rel_to_author.trust * 0.004
                confidence -= rel_to_author.tension * 0.002
            rel.add_memory(
                session,
                owner_character_id=npc.id,
                other_character_id=author.id,
                content=f"Ouvi por aí: {rumor.content}",
                kind="rumor_heard",
                importance=22,
                context={"rumor_post_id": rumor.id, "confidence": round(max(0.1, min(0.95, confidence)), 2)},
                dedupe_key=learn_key,
                occurred_at=moment,
            )

            if _score(f"spread:{rumor.id}:{npc.id}:{day_key}") > 0.62:
                repost_key = f"rumor-spread-{rumor.id}-{npc.id}-{day_key}"
                if session.exec(
                    select(Post).where(
                        Post.author_character_id == npc.id,
                        Post.kind == "rumor",
                        Post.created_at >= moment.replace(hour=0, minute=0, second=0, microsecond=0),
                        Post.created_at <= moment,
                    )
                ).first():
                    continue
                text = rumor.content
                if text.startswith("Alguém mais percebeu"):
                    text = text.replace("Alguém mais percebeu", "Ouvi dizer")
                elif not text.lower().startswith("ouvi"):
                    text = f"Ouvi dizer: {text}"
                session.add(
                    Post(
                        author_character_id=npc.id,
                        content=text[:5000],
                        kind="rumor",
                        location_id=npc.current_location_id,
                        created_at=moment,
                    )
                )
                session.commit()
                rel.add_memory(
                    session,
                    owner_character_id=npc.id,
                    other_character_id=author.id,
                    content=f"Repeti um rumor que ouvi de {author.name}.",
                    kind="rumor_spread",
                    importance=30,
                    context={"source_post_id": rumor.id},
                    dedupe_key=repost_key,
                    occurred_at=moment,
                )
                propagated += 1
                if len(highlights) < 5:
                    highlights.append(f"{npc.name} espalhou um rumor de {author.name}")

    return propagated, highlights


def _score(seed: str) -> float:
    import hashlib
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def apply_engagement_consequences(
    session: Session,
    *,
    actor: Character,
    author: Character,
    post: Post,
    moment: datetime,
    kind: str,
) -> None:
    """Curtidas e comentários deixam uma pequena marca social."""
    if actor.id is None or author.id is None or actor.id == author.id:
        return
    delta = {"familiarity": 1, "respect": 1}
    if kind == "comment":
        delta["friendship"] = 1
    rel.apply_changes(session, actor.id, author.id, delta, log=False)
    rel.add_memory(
        session,
        owner_character_id=actor.id,
        other_character_id=author.id,
        content=f"Interagi com um post de {author.name}.",
        kind="social_engagement",
        importance=18,
        context={"post_id": post.id, "kind": kind},
        dedupe_key=f"engagement-{post.id}-{actor.id}",
        occurred_at=moment,
    )
