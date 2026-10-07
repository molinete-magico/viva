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

from app.models import Character, Event, EventParticipant, Follow, Memory, Notification, Post, Relationship
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


def advance_social_intentions(
    session: Session,
    moment: datetime,
) -> tuple[int, list[str]]:
    """Transforma o arco atual em uma iniciativa social concreta.

    Cada par recebe no máximo uma iniciativa por dia. As iniciativas são
    deliberadamente pequenas: uma DM, um convite, uma tentativa de reconciliação
    ou uma provocação pública. O efeito é persistente e pode alimentar a próxima
    janela da simulação.
    """
    from app.services.messaging_service import send_npc_initiative

    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    players = session.exec(select(Character).where(Character.is_npc.is_(False))).all()
    characters = {c.id: c for c in npcs + players if c.id is not None}
    relationships = session.exec(select(Relationship)).all()
    actions = 0
    highlights: list[str] = []
    day = moment.date().isoformat()

    for relationship in relationships:
        left = characters.get(relationship.character_a_id)
        right = characters.get(relationship.character_b_id)
        if left is None or right is None:
            continue

        arc = relationship_arc(relationship)
        if arc == "acquaintance":
            continue

        # Só NPCs tomam iniciativas autônomas. Se os dois são NPCs, a cidade
        # continua se movendo sem depender do jogador.
        actor = left if left.is_npc else right if right.is_npc else None
        target = right if actor is left else left if actor is right else None
        if actor is None or target is None or actor.id is None or target.id is None:
            continue

        key = f"social-intent-{actor.id}-{target.id}-{day}"
        if session.exec(
            select(Memory).where(
                Memory.owner_character_id == actor.id,
                Memory.dedupe_key == key,
            )
        ).first():
            continue

        # A pontuação é determinística para que catch-up repetido não produza
        # comportamentos diferentes sem mudança no estado do mundo.
        chance = {
            "friendship": 0.58,
            "romance": 0.72,
            "rivalry": 0.48,
            "strained": 0.42,
            "budding_friendship": 0.34,
        }.get(arc, 0.2)
        energy = float((actor.personality or {}).get("energy", 0.5))
        social_drive = float((actor.personality or {}).get("sociability", (actor.personality or {}).get("social", 0.5)))
        if _score(f"intent:{actor.id}:{target.id}:{day}") > min(0.92, chance + energy * 0.08 + social_drive * 0.06):
            continue

        message: str | None = None
        kind = "social_intent"
        changes: dict[str, int] = {}

        if arc == "friendship":
            hobby = (target.hobbies or actor.hobbies or ["dar uma volta"])[0]
            message = f"Ei, {target.name}. Pensei em você hoje. Quer fazer alguma coisa juntos? Talvez algo envolvendo {hobby}."
            changes = {"familiarity": 1, "friendship": 2, "trust": 1}
        elif arc == "budding_friendship":
            message = f"Oi, {target.name}! A gente tem se esbarrado bastante. Quer conversar qualquer hora?"
            changes = {"familiarity": 2, "friendship": 1}
        elif arc == "romance":
            message = f"Você me veio à cabeça hoje, {target.name}. Quer me encontrar mais tarde?"
            changes = {"familiarity": 1, "romance": 1}
        elif arc == "strained":
            message = f"Ei, {target.name}. Acho que as coisas ficaram estranhas entre a gente. Não quero deixar assim."
            changes = {"familiarity": 1, "tension": -2, "trust": 1}
            kind = "reconciliation_attempt"
        elif arc == "rivalry":
            # Rivalidade não precisa virar briga toda vez: uma provocação pública
            # cria pressão social e deixa espaço para terceiros reagirem.
            post = Post(
                author_character_id=actor.id,
                content=f"Tem gente que transforma qualquer conversa em competição. Cansativo.",
                kind="post",
                location_id=actor.current_location_id,
                created_at=moment,
            )
            session.add(post)
            session.commit()
            rel.add_memory(
                session,
                owner_character_id=actor.id,
                other_character_id=target.id,
                content=f"Fiz uma provocação indireta pensando em {target.name}.",
                kind="rivalry_action",
                importance=36,
                context={"arc": arc},
                dedupe_key=key,
                occurred_at=moment,
            )
            rel.apply_changes(session, actor.id, target.id, {"tension": 1, "respect": 1}, log=False)
            actions += 1
            if len(highlights) < 6:
                highlights.append(f"{actor.name} provocou alguém em público")
            continue

        if arc in ("friendship", "romance") and actor.current_location_id is not None and _score(f"meetup:{actor.id}:{target.id}:{day}") < (0.28 if arc == "friendship" else 0.42):
            event = Event(
                title=("Encontro com " if arc == "romance" else "Rolê com ") + target.name,
                description=f"{actor.name} tomou a iniciativa de encontrar {target.name}.",
                location_id=actor.current_location_id,
                host_character_id=actor.id,
                created_by="system",
                scheduled_at=moment + timedelta(hours=1),
                status="OPEN",
                kind="social_arc",
                max_participants=2,
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            session.add(EventParticipant(event_id=event.id, character_id=actor.id, status="JOINED", responded_at=moment, joined_at=moment))
            session.add(EventParticipant(event_id=event.id, character_id=target.id, status="INVITED"))
            if target.user_id is not None:
                session.add(Notification(character_id=target.id, type="EVENT_INVITE", payload={"event_id": event.id, "title": event.title, "scheduled_at": event.scheduled_at.isoformat(), "host_id": actor.id}))
            session.commit()
            message = f"Quero te ver mais tarde, {target.name}. Separei um encontro para nós. Se puder, aparece."
            kind = "social_invitation"
            changes = {"familiarity": 1, "friendship": 2 if arc == "friendship" else 1, "romance": 1 if arc == "romance" else 0}
        try:
            send_npc_initiative(session, actor, target, message)
        except Exception:
            continue

        rel.apply_changes(session, actor.id, target.id, changes, log=False)
        rel.add_memory(
            session,
            owner_character_id=actor.id,
            other_character_id=target.id,
            content=f"Tomei uma iniciativa com {target.name}: {message}",
            kind=kind,
            importance=40 if arc != "romance" else 48,
            context={"arc": arc, "world_time": moment.isoformat()},
            dedupe_key=key,
            occurred_at=moment,
        )
        rel.add_memory(
            session,
            owner_character_id=target.id,
            other_character_id=actor.id,
            content=f"{actor.name} tomou uma iniciativa comigo enquanto nossa relação estava em uma fase de {arc.replace('_', ' ')}.",
            kind="received_social_intent",
            importance=34,
            context={"arc": arc, "world_time": moment.isoformat()},
            dedupe_key=f"{key}-received",
            occurred_at=moment,
        )
        actions += 1
        if len(highlights) < 6:
            highlights.append(f"{actor.name} tomou uma iniciativa com {target.name} ({arc.replace('_', ' ')})")

    return actions, highlights
