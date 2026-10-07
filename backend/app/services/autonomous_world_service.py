"""Camada de dinâmica social contínua.

Complementa o motor de autonomia com manutenção do grafo social, respostas,
eventos ambientais, reputação, rumores e pequenas consequências que continuam
existindo sem o jogador. Todas as decisões de domínio são determinísticas e
persistidas; o LLM permanece opcional para a superfície narrativa.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models import (
    Character,
    Comment,
    Event,
    EventParticipant,
    Follow,
    Like,
    Location,
    Memory,
    Notification,
    Post,
    Relationship,
)
from app.services import relationship_service as rel


def _score(seed: str) -> float:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def _arc(r: Relationship | None) -> str:
    if r is None:
        return "acquaintance"
    if r.romance >= 45:
        return "romance"
    if r.tension >= 45 and r.friendship < 35:
        return "rivalry"
    if r.friendship >= 55 and r.trust >= 35:
        return "friendship"
    if r.tension >= 25:
        return "strained"
    if r.friendship >= 25 or r.familiarity >= 20:
        return "budding_friendship"
    return "acquaintance"


def _marker(session: Session, owner_id: int, key: str) -> bool:
    return session.exec(
        select(Memory).where(
            Memory.owner_character_id == owner_id,
            Memory.dedupe_key == key,
        )
    ).first() is not None


def _remember(
    session: Session,
    owner: Character,
    other: Character | None,
    content: str,
    *,
    kind: str,
    key: str,
    moment: datetime,
    importance: int = 30,
) -> None:
    if owner.id is None or _marker(session, owner.id, key):
        return
    rel.add_memory(
        session,
        owner_character_id=owner.id,
        other_character_id=other.id if other else None,
        content=content[:4000],
        kind=kind,
        importance=importance,
        context={"world_time": moment.isoformat()},
        dedupe_key=key,
        occurred_at=moment,
    )


def _social_fit(npc: Character, other: Character, relationship: Relationship | None) -> float:
    score = 0.0
    left = {str(x).lower() for x in (npc.hobbies or []) + (npc.likes or [])}
    right = {str(x).lower() for x in (other.hobbies or []) + (other.likes or [])}
    score += min(3.0, len(left & right) * 1.2)
    dislikes = {str(x).lower() for x in (npc.dislikes or [])}
    score -= min(3.0, len(dislikes & right) * 1.5)
    if relationship:
        score += relationship.friendship * 0.035
        score += relationship.trust * 0.02
        score += relationship.respect * 0.015
        score -= relationship.tension * 0.04
    return score


def _daily_key(prefix: str, a: int, b: int, moment: datetime) -> str:
    return f"{prefix}-{min(a,b)}-{max(a,b)}-{moment.date().isoformat()}"


def maintain_social_graph(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Faz o grafo refletir relações reais: aproxima, segue, ou se afasta."""
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    changes = 0
    highlights: list[str] = []
    for i, npc in enumerate(npcs):
        if npc.id is None:
            continue
        for other in npcs[i + 1 :]:
            if other.id is None:
                continue
            relationship = rel.relationship_between(session, npc.id, other.id)
            fit = _social_fit(npc, other, relationship)
            follows = session.exec(
                select(Follow).where(
                    Follow.follower_character_id == npc.id,
                    Follow.followed_character_id == other.id,
                )
            ).first()
            key = _daily_key("graph", npc.id, other.id, moment)
            if _marker(session, npc.id, key):
                continue

            should_follow = fit >= 1.5 and (relationship is None or relationship.tension < 65)
            should_unfollow = follows is not None and relationship is not None and relationship.tension >= 68
            if should_unfollow:
                session.delete(follows)
                session.commit()
                _remember(session, npc, other, f"Deixei de acompanhar {other.name}; nossa relação ficou pesada demais.", kind="social_graph_change", key=key, moment=moment, importance=34)
                changes += 1
                highlights.append(f"{npc.name} se afastou de {other.name}")
            elif should_follow and follows is None and _score(f"follow:{key}:{npc.id}") < min(0.88, 0.45 + fit * 0.08):
                session.add(Follow(follower_character_id=npc.id, followed_character_id=other.id))
                session.commit()
                _remember(session, npc, other, f"Passei a acompanhar {other.name}; quero ver mais do que essa pessoa anda fazendo.", kind="social_graph_change", key=key, moment=moment, importance=28)
                changes += 1
                highlights.append(f"{npc.name} começou a acompanhar {other.name}")
    return changes, highlights[:8]


def settle_relationship_tension(session: Session, moment: datetime) -> int:
    """Tensão não fica congelada para sempre: sem contato, conflitos podem esfriar."""
    relationships = session.exec(select(Relationship)).all()
    changed = 0
    for relationship in relationships:
        if relationship.tension <= 0:
            continue
        if relationship.last_interaction_at and moment - relationship.last_interaction_at < timedelta(days=1):
            continue
        key = f"tension-cooldown-{relationship.id}-{moment.date().isoformat()}"
        if _marker(session, relationship.character_a_id, key):
            continue
        relationship.tension = max(0, relationship.tension - 1)
        relationship.updated_at = moment
        session.add(relationship)
        session.commit()
        a = session.get(Character, relationship.character_a_id)
        if a:
            _remember(session, a, session.get(Character, relationship.character_b_id), "A tensão daquela relação diminuiu um pouco com o passar dos dias.", kind="relationship_cooldown", key=key, moment=moment, importance=18)
        changed += 1
    return changed


def resolve_ambient_events(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """NPCs aceitam convites e encerram pequenas atividades sem precisar do jogador."""
    events = session.exec(
        select(Event).where(
            Event.kind == "ambient",
            Event.status == "OPEN",
            Event.scheduled_at <= moment,
        ).order_by(Event.id.asc()).limit(8)
    ).all()
    completed = 0
    highlights: list[str] = []
    for event in events:
        participants = session.exec(
            select(EventParticipant).where(EventParticipant.event_id == event.id)
        ).all()
        joined: list[Character] = []
        for participant in participants:
            character = session.get(Character, participant.character_id)
            if character is None or not character.is_npc:
                continue
            if participant.status == "INVITED":
                if _score(f"rsvp:{event.id}:{character.id}") < 0.72:
                    participant.status = "ACCEPTED"
                    participant.responded_at = moment
                    session.add(participant)
            if participant.status in ("ACCEPTED", "JOINED"):
                participant.status = "JOINED"
                participant.joined_at = participant.joined_at or moment
                session.add(participant)
                joined.append(character)

        host = session.get(Character, event.host_character_id) if event.host_character_id else None
        if host and host not in joined:
            joined.insert(0, host)

        if len(joined) >= 1:
            for index, left in enumerate(joined):
                for right in joined[index + 1 :]:
                    if left.id is None or right.id is None:
                        continue
                    rel.apply_changes(
                        session,
                        left.id,
                        right.id,
                        {"familiarity": 1, "friendship": 1, "respect": 1},
                        log=False,
                    )
                    key = f"ambient-event-{event.id}-{min(left.id,right.id)}-{max(left.id,right.id)}"
                    _remember(session, left, right, f"Participei de {event.title} com {right.name}.", kind="ambient_event", key=key, moment=moment, importance=32)
                    _remember(session, right, left, f"Participei de {event.title} com {left.name}.", kind="ambient_event", key=f"{key}-r", moment=moment, importance=32)
            event.status = "COMPLETED"
            session.add(event)
            session.commit()
            completed += 1
            highlights.append(f"{event.title} aconteceu com {len(joined)} participante(s)")
    return completed, highlights[:8]


def propagate_social_reactions(session: Session, moment: datetime) -> tuple[int, int, list[str]]:
    """Reações NPC tornam posts em pequenas cadeias sociais, não só contadores."""
    cutoff = moment - timedelta(hours=18)
    posts = session.exec(
        select(Post).where(Post.created_at >= cutoff).order_by(Post.id.desc()).limit(40)
    ).all()
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    likes = comments = 0
    highlights: list[str] = []
    for post in posts:
        author = session.get(Character, post.author_character_id)
        if author is None:
            continue
        candidates: list[Character] = []
        for npc in npcs:
            if npc.id == author.id:
                continue
            relationship = rel.relationship_between(session, npc.id, author.id)
            follows = session.exec(select(Follow).where(Follow.follower_character_id == npc.id, Follow.followed_character_id == author.id)).first()
            if follows is not None or (relationship and relationship.friendship >= 35):
                candidates.append(npc)
        candidates.sort(key=lambda n: _social_fit(n, author, rel.relationship_between(session, n.id, author.id)), reverse=True)
        for npc in candidates[:2]:
            if npc.id is None:
                continue
            existing = session.exec(select(Like).where(Like.target_type == "post", Like.target_id == post.id, Like.character_id == npc.id)).first()
            if existing is None and _score(f"like:{post.id}:{npc.id}") < 0.82:
                session.add(Like(target_type="post", target_id=post.id, character_id=npc.id))
                session.commit()
                rel.apply_changes(session, npc.id, author.id, {"familiarity": 1, "respect": 1}, log=False)
                if not author.is_npc and _score(f"follow-after-like:{post.id}:{npc.id}") < 0.22:
                    existing_follow = session.exec(select(Follow).where(Follow.follower_character_id == npc.id, Follow.followed_character_id == author.id)).first()
                    if existing_follow is None:
                        session.add(Follow(follower_character_id=npc.id, followed_character_id=author.id))
                        session.add(Notification(character_id=author.id, type="NEW_FOLLOWER", payload={"character_id": npc.id, "name": npc.name, "reason": "interagiu_com_seus_posts"}))
                        session.commit()
                likes += 1
            if comments == 0 and _score(f"reply:{post.id}:{npc.id}") > 0.72:
                existing_comment = session.exec(select(Comment).where(Comment.post_id == post.id, Comment.author_character_id == npc.id)).first()
                if existing_comment is None:
                    text = f"Vi isso e lembrei de {((npc.hobbies or ['uma coisa'])[0])}. Faz sentido."
                    session.add(Comment(post_id=post.id, author_character_id=npc.id, content=text[:2000], created_at=moment))
                    session.commit()
                    rel.apply_changes(session, npc.id, author.id, {"familiarity": 1, "friendship": 1}, log=False)
                    if not author.is_npc and _score(f"follow-after-comment:{post.id}:{npc.id}") < 0.55:
                        existing_follow = session.exec(select(Follow).where(Follow.follower_character_id == npc.id, Follow.followed_character_id == author.id)).first()
                        if existing_follow is None:
                            session.add(Follow(follower_character_id=npc.id, followed_character_id=author.id))
                            session.add(Notification(character_id=author.id, type="NEW_FOLLOWER", payload={"character_id": npc.id, "name": npc.name, "reason": "respondeu_seu_post"}))
                            session.commit()
                    comments += 1
                    highlights.append(f"{npc.name} respondeu a uma publicação de {author.name}")
                    break
    return likes, comments, highlights[:6]


def spread_rumor_chain(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Rumores ganham segunda e terceira mão com alcance limitado e rastreável."""
    cutoff = moment - timedelta(hours=24)
    rumors = session.exec(select(Post).where(Post.kind == "rumor", Post.created_at >= cutoff).order_by(Post.id.desc()).limit(20)).all()
    spread = 0
    highlights: list[str] = []
    for rumor in rumors:
        author = session.get(Character, rumor.author_character_id)
        if author is None:
            continue
        followers = session.exec(select(Follow).where(Follow.followed_character_id == author.id)).all()
        for follow in followers[:4]:
            listener = session.get(Character, follow.follower_character_id)
            if listener is None or not listener.is_npc:
                continue
            key = f"heard-rumor-{rumor.id}-{listener.id}"
            if _marker(session, listener.id, key):
                continue
            confidence = 0.55
            relationship = rel.relationship_between(session, listener.id, author.id)
            if relationship:
                confidence += relationship.trust * 0.004
                confidence -= relationship.tension * 0.003
            _remember(session, listener, author, f"Ouvi um rumor: {rumor.content}", kind="rumor_heard", key=key, moment=moment, importance=24)
            spread += 1
            if _score(f"repeat:{rumor.id}:{listener.id}") < max(0.08, min(0.65, confidence * 0.45)):
                repost = Post(
                    author_character_id=listener.id,
                    content=f"Ouvi dizer que: {rumor.content.removeprefix('Alguém mais percebeu que ')}",
                    kind="rumor",
                    location_id=listener.current_location_id,
                    created_at=moment,
                )
                session.add(repost)
                session.commit()
                highlights.append(f"{listener.name} repassou um rumor")
    return spread, highlights[:8]


def update_reputation(session: Session, moment: datetime) -> int:
    """Popularidade passa a ter efeito observável no nível de descoberta."""
    characters = session.exec(select(Character)).all()
    changed = 0
    cutoff = moment - timedelta(days=7)
    for character in characters:
        if character.id is None:
            continue
        posts = session.exec(select(Post).where(Post.author_character_id == character.id, Post.created_at >= cutoff)).all()
        if not posts:
            continue
        post_ids = [p.id for p in posts]
        likes = len(session.exec(select(Like).where(Like.target_type == "post", Like.target_id.in_(post_ids))).all()) if post_ids else 0
        comments = len(session.exec(select(Comment).where(Comment.post_id.in_(post_ids))).all()) if post_ids else 0
        target = min(10, 1 + (likes // 4) + (comments // 2))
        if target > character.discovered_level:
            character.discovered_level = target
            session.add(character)
            changed += 1
    if changed:
        session.commit()
    return changed


def run_social_dynamics(session: Session, moment: datetime) -> dict:
    graph, graph_highlights = maintain_social_graph(session, moment)
    cooled = settle_relationship_tension(session, moment)
    events, event_highlights = resolve_ambient_events(session, moment)
    likes, comments, reaction_highlights = propagate_social_reactions(session, moment)
    rumors, rumor_highlights = spread_rumor_chain(session, moment)
    reputation = update_reputation(session, moment)
    return {
        "graph_changes": graph,
        "tension_cooled": cooled,
        "events_resolved": events,
        "likes": likes,
        "comments": comments,
        "rumors": rumors,
        "reputation_updates": reputation,
        "highlights": (
            graph_highlights + event_highlights + reaction_highlights + rumor_highlights
        )[:12],
    }


def city_pulse(session: Session, moment: datetime) -> dict:
    """Resumo curto do que está acontecendo agora e do que mudou recentemente."""
    cutoff = moment - timedelta(hours=12)
    posts = session.exec(
        select(Post).where(Post.created_at >= cutoff).order_by(Post.id.desc()).limit(12)
    ).all()
    events = session.exec(
        select(Event).where(Event.scheduled_at >= cutoff).order_by(Event.scheduled_at.desc()).limit(8)
    ).all()
    memories = session.exec(
        select(Memory).where(Memory.occurred_at >= cutoff, Memory.importance >= 35)
        .order_by(Memory.importance.desc(), Memory.occurred_at.desc()).limit(10)
    ).all()
    characters = {c.id: c for c in session.exec(select(Character)).all()}
    return {
        "generated_at": moment.isoformat(),
        "recent_posts": [
            {
                "id": post.id,
                "author_id": post.author_character_id,
                "author_name": characters.get(post.author_character_id).name if characters.get(post.author_character_id) else "Morador",
                "kind": post.kind,
                "content": post.content,
                "created_at": post.created_at.isoformat(),
            }
            for post in posts
        ],
        "recent_events": [
            {
                "id": event.id,
                "title": event.title,
                "status": event.status,
                "scheduled_at": event.scheduled_at.isoformat(),
                "host_name": characters.get(event.host_character_id).name if event.host_character_id and characters.get(event.host_character_id) else "cidade",
            }
            for event in events
        ],
        "social_highlights": [
            {
                "character_id": memory.owner_character_id,
                "character_name": characters.get(memory.owner_character_id).name if characters.get(memory.owner_character_id) else "Morador",
                "kind": memory.kind,
                "content": memory.content,
                "importance": memory.importance,
                "occurred_at": memory.occurred_at.isoformat(),
            }
            for memory in memories
        ],
    }
