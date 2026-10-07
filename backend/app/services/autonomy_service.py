"""Motor de vida autônoma da Vila Serena.

Este módulo não espera uma ação do jogador para produzir atividade. O relógio do
mundo percorre os intervalos em que o app ficou fechado e transforma rotinas,
locais, relações, objetivos e personalidade em pequenos acontecimentos sociais.
O LLM escreve a superfície; este serviço decide quando e quem pode agir.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from itertools import combinations

from sqlmodel import Session, select

from app.models import Character, Comment, Event, EventParticipant, Follow, Like, Location, Memory, Notification, Post, Schedule, WorldState
from app.services import relationship_service as rel


def _score(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _schedule_for(session: Session, npc: Character, moment: datetime) -> Schedule | None:
    rows = session.exec(
        select(Schedule).where(
            Schedule.character_id == npc.id,
            (Schedule.day_of_week.is_(None)) | (Schedule.day_of_week == moment.weekday()),
        )
    ).all()
    current = moment.time()
    candidates: list[Schedule] = []
    for row in rows:
        try:
            start = datetime.strptime(row.start_time, "%H:%M").time()
            end = datetime.strptime(row.end_time, "%H:%M").time()
        except ValueError:
            continue
        if start <= end:
            inside = start <= current <= end
        else:
            inside = current >= start or current <= end
        if inside:
            candidates.append(row)
    return candidates[-1] if candidates else None


def update_npc_locations(session: Session, moment: datetime) -> int:
    changed = 0
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    for npc in npcs:
        schedule = _schedule_for(session, npc, moment)
        location_id = schedule.location_id if schedule else None
        if npc.current_location_id != location_id:
            npc.current_location_id = location_id
            session.add(npc)
            changed += 1
    if changed:
        session.commit()
    return changed


def _nearby_groups(session: Session) -> dict[int, list[Character]]:
    npcs = session.exec(
        select(Character).where(
            Character.is_npc.is_(True),
            Character.current_location_id.is_not(None),
        )
    ).all()
    groups: dict[int, list[Character]] = {}
    for npc in npcs:
        if npc.current_location_id is not None:
            groups.setdefault(npc.current_location_id, []).append(npc)
    return groups


def _interact(session: Session, left: Character, right: Character, location: Location, moment: datetime) -> bool:
    if left.id is None or right.id is None:
        return False
    relationship = rel.relationship_between(session, left.id, right.id)
    if relationship is not None and relationship.last_interaction_at:
        # last_interaction_at is normally wall-clock data; only use it as a
        # conservative anti-spam guard for interactions generated this run.
        if relationship.last_interaction_at > datetime.now(timezone.utc) - timedelta(minutes=20):
            return False

    energy = float((left.personality or {}).get("energy", 0.5)) + float((right.personality or {}).get("energy", 0.5))
    friendship_delta = 2 if energy >= 1.1 else 1
    tension = 2 if any(
        str(item).lower() in " ".join(map(str, right.dislikes or [])).lower()
        for item in (left.hobbies or [])[:2]
    ) else 0
    if tension:
        friendship_delta = 0
    romance = 1 if _score(f"romance:{moment.isoformat()}:{left.id}:{right.id}") > 0.94 else 0
    relationship = rel.apply_changes(
        session,
        left.id,
        right.id,
        {"familiarity": 1, "friendship": friendship_delta, "respect": 1, "tension": tension, "romance": romance},
        log=True,
    )
    relationship.last_interaction_at = moment
    session.add(relationship)
    session.commit()

    stamp = moment.strftime("%Y%m%d%H")
    for owner, other in ((left, right), (right, left)):
        rel.add_memory(
            session,
            owner_character_id=owner.id,
            other_character_id=other.id,
            content=f"Encontrei {other.name} em {location.name}; a conversa aconteceu enquanto a cidade seguia sua rotina.",
            category="NORMAL",
            kind="npc_encounter",
            importance=28,
            context={"location_id": location.id, "world_time": moment.isoformat()},
            dedupe_key=f"ambient-{owner.id}-{other.id}-{stamp}",
            occurred_at=moment,
        )
    return True


def _post_exists_today(session: Session, npc_id: int, moment: datetime) -> bool:
    rows = session.exec(
        select(Post).where(Post.author_character_id == npc_id).order_by(Post.id.desc()).limit(8)
    ).all()
    return any(
        post.created_at.year == moment.year
        and post.created_at.month == moment.month
        and post.created_at.day == moment.day
        for post in rows
    )


def _npc_social_graph(session: Session, npcs: list[Character]) -> None:
    """Garante uma pequena rede inicial entre NPCs, sem transformar todos em amigos."""
    for left, right in combinations(npcs, 2):
        if left.id is None or right.id is None:
            continue
        if _score(f"follow:{left.id}:{right.id}") > 0.78:
            exists = session.exec(
                select(Follow).where(
                    Follow.follower_character_id == left.id,
                    Follow.followed_character_id == right.id,
                )
            ).first()
            if exists is None:
                session.add(Follow(follower_character_id=left.id, followed_character_id=right.id))
    session.commit()


def _daily_activity(session: Session, moment: datetime) -> bool:
    """Cria uma atividade pública pequena por dia, com NPCs como autores."""
    if not (17 <= moment.hour <= 21):
        return False
    start = datetime.combine(moment.date(), datetime.min.time(), tzinfo=moment.tzinfo)
    end = start + timedelta(days=1)
    existing = session.exec(
        select(Event).where(
            Event.kind == "ambient",
            Event.scheduled_at >= start,
            Event.scheduled_at < end,
        )
    ).first()
    if existing is not None:
        return False

    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    candidates = [npc for npc in npcs if npc.current_location_id is not None]
    if not candidates:
        return False
    host = max(
        candidates,
        key=lambda npc: float((npc.personality or {}).get("energy", 0.5)),
    )
    location = session.get(Location, host.current_location_id)
    if location is None:
        return False

    activity = (location.activities or ["um encontro espontâneo"])[0]
    event = Event(
        title=f"{activity.capitalize()} no {location.name}",
        description=f"Uma atividade espontânea organizada por {host.name}. Quem aparecer pode acabar conhecendo gente nova.",
        location_id=location.id,
        host_character_id=host.id,
        created_by="system",
        scheduled_at=moment,
        status="OPEN",
        kind="ambient",
        max_participants=5,
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    nearby = [
        npc for npc in candidates
        if npc.id != host.id and npc.current_location_id == location.id
    ][:4]
    for npc in nearby:
        session.add(EventParticipant(event_id=event.id, character_id=npc.id, status="JOINED"))
    session.commit()

    players = session.exec(select(Character).where(Character.is_npc.is_(False))).all()
    if players:
        from app.services.messaging_service import send_npc_initiative
        for player in players[:1]:
            try:
                send_npc_initiative(
                    session,
                    host,
                    player,
                    f"Ei, {player.name}! Vai rolar {event.title.lower()} hoje. Eu vou estar lá. Se aparecer, me procura.",
                )
            except Exception:
                pass
    return True


def _ensure_player_social_entry(session: Session, players: list[Character], npcs: list[Character]) -> None:
    """Todo personagem novo entra no mundo já com uma primeira conexão social."""
    for player in players:
        if player.id is None:
            continue
        existing = session.exec(
            select(Follow).where(
                Follow.followed_character_id == player.id,
                Follow.follower_character_id.in_([npc.id for npc in npcs if npc.id is not None]),
            )
        ).first()
        if existing is not None:
            continue
        candidates = sorted(
            npcs,
            key=lambda npc: _score(f"starter:{player.id}:{npc.id}"),
            reverse=True,
        )
        if not candidates:
            continue
        npc = candidates[0]
        if npc.id is None:
            continue
        session.add(Follow(follower_character_id=npc.id, followed_character_id=player.id))
        session.add(
            Notification(
                character_id=player.id,
                type="NEW_FOLLOWER",
                payload={"character_id": npc.id, "name": npc.name, "reason": "morador_da_cidade"},
            )
        )
        session.commit()
        rel.apply_changes(
            session,
            npc.id,
            player.id,
            {"familiarity": 2, "respect": 1},
            log=False,
        )
        rel.add_memory(
            session,
            owner_character_id=npc.id,
            other_character_id=player.id,
            content=f"Comecei a acompanhar {player.name}; quero descobrir quem é essa pessoa nova na Vila Serena.",
            kind="first_contact",
            importance=38,
            dedupe_key=f"first-contact-{npc.id}-{player.id}",
            occurred_at=datetime.now(timezone.utc),
        )


def _proactive_player_contact(session: Session, moment: datetime) -> int:
    """Um NPC com motivo social pode procurar o jogador sem ser provocado."""
    players = session.exec(select(Character).where(Character.is_npc.is_(False))).all()
    if not players:
        return 0
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    sent = 0

    from app.services.messaging_service import send_npc_initiative

    for player in players:
        candidates: list[tuple[int, Character]] = []
        for npc in npcs:
            if npc.id is None or player.id is None:
                continue
            relationship = rel.relationship_between(session, npc.id, player.id)
            score = 0
            if relationship is not None:
                score = (
                    relationship.friendship
                    + relationship.familiarity
                    + relationship.trust
                    + relationship.respect
                    - relationship.tension
                )
            follows = session.exec(
                select(Follow).where(
                    Follow.follower_character_id == npc.id,
                    Follow.followed_character_id == player.id,
                )
            ).first()
            if follows is not None:
                score += 6
            if score >= 2:
                candidates.append((score, npc))

        if not candidates:
            continue
        candidates.sort(key=lambda item: (item[0], item[1].id or 0), reverse=True)
        npc = candidates[0][1]
        dedupe = f"initiative-{npc.id}-{player.id}-{moment.date().isoformat()}"
        if session.exec(select(Memory).where(Memory.owner_character_id == npc.id, Memory.dedupe_key == dedupe)).first():
            continue

        hobby = (npc.hobbies or ["a cidade"])[0]
        location = session.get(Location, npc.current_location_id) if npc.current_location_id else None
        place = location.name if location else "por aqui"
        message = (
            f"Ei, {player.name}. Estou em {place} agora e lembrei de você. "
            f"Você ainda curte {hobby}? Tô com vontade de fazer alguma coisa diferente hoje."
        )
        try:
            send_npc_initiative(session, npc, player, message)
        except Exception:
            continue
        rel.add_memory(
            session,
            owner_character_id=npc.id,
            other_character_id=player.id,
            content=f"Procurei {player.name} por iniciativa própria porque estava pensando em {hobby}.",
            category="NORMAL",
            kind="npc_initiative",
            importance=32,
            dedupe_key=dedupe,
            occurred_at=moment,
        )
        sent += 1
    return sent


def simulate_social_life(session: Session, from_dt: datetime, until_dt: datetime) -> dict:
    """Avança a vida social em fatias, em vez de gerar um único pulso no retorno."""
    if until_dt <= from_dt:
        return {"interactions": 0, "posts": 0, "comments": 0, "likes": 0, "locations": 0, "activities": 0, "proactive_dms": 0}

    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    _npc_social_graph(session, npcs)

    interactions = posts = comments = likes = locations = activities = proactive_dms = 0
    cursor = from_dt + timedelta(minutes=30)

    from app.services.llm_service import generate_npc_comment, generate_npc_post

    while cursor <= until_dt:
        locations += update_npc_locations(session, cursor)
        if _daily_activity(session, cursor):
            activities += 1
        if cursor.hour in (18, 21) and cursor.minute < 90:
            proactive_dms += _proactive_player_contact(session, cursor)
        groups = _nearby_groups(session)

        for location_id, occupants in groups.items():
            if len(occupants) < 2:
                continue
            location = session.get(Location, location_id)
            if location is None:
                continue

            # No máximo dois encontros por janela. A cidade é viva, não uma máquina
            # de gerar spam.
            ranked = sorted(
                combinations(occupants, 2),
                key=lambda pair: _score(f"meet:{cursor.isoformat()}:{pair[0].id}:{pair[1].id}"),
                reverse=True,
            )
            for left, right in ranked[:2]:
                chance = 0.35 + 0.25 * float((left.personality or {}).get("energy", 0.5))
                if _score(f"chance:{cursor.isoformat()}:{left.id}:{right.id}") <= chance:
                    if _interact(session, left, right, location, cursor):
                        interactions += 1

        # Alguns moradores publicam espontaneamente. O limite por dia evita uma
        # avalanche e deixa espaço para os posts do jogador respirarem.
        candidates = sorted(
            npcs,
            key=lambda npc: _score(f"post:{cursor.isoformat()}:{npc.id}"),
            reverse=True,
        )
        made_here: list[Post] = []
        for npc in candidates[:2]:
            if _post_exists_today(session, npc.id, cursor):
                continue
            energy = float((npc.personality or {}).get("energy", 0.5))
            if _score(f"post-chance:{cursor.isoformat()}:{npc.id}") > 0.18 + energy * 0.08:
                continue
            try:
                post = generate_npc_post(session, npc, simulated_at=cursor)
            except Exception:
                continue
            made_here.append(post)
            posts += 1

        # Posts de NPCs ganham vida de outros NPCs: poucas curtidas e uma resposta
        # quando há afinidade suficiente. Isso cria conversas públicas persistentes.
        for post in made_here:
            author = session.get(Character, post.author_character_id)
            if author is None:
                continue
            followers = session.exec(
                select(Follow).where(Follow.followed_character_id == author.id)
            ).all()
            follower_ids = [row.follower_character_id for row in followers]
            actors = [
                npc for npc in npcs
                if npc.id in follower_ids and npc.id != author.id
            ]
            for actor in actors[:2]:
                existing = session.exec(
                    select(Like).where(
                        Like.target_type == "post",
                        Like.target_id == post.id,
                        Like.character_id == actor.id,
                    )
                ).first()
                if existing is None:
                    session.add(Like(target_type="post", target_id=post.id, character_id=actor.id))
                    session.commit()
                    likes += 1

            if actors and _score(f"comment:{post.id}") > 0.45:
                try:
                    text = generate_npc_comment(session, actors[0], post)
                except Exception:
                    text = ""
                if text.strip():
                    session.add(Comment(post_id=post.id, author_character_id=actors[0].id, content=text[:2000], created_at=cursor))
                    session.commit()
                    comments += 1

        cursor += timedelta(minutes=90)

    return {
        "interactions": interactions,
        "posts": posts,
        "comments": comments,
        "likes": likes,
        "locations": locations,
        "activities": activities,
        "proactive_dms": proactive_dms,
    }
