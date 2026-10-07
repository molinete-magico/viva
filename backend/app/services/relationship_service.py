from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from app.domain.errors import ServiceError
from app.domain.events import DIMENSIONS
from app.models import Character, Memory, Relationship
from app.models.base import utcnow

MAX_DIMENSION = 100


def canonical_pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a <= b else (b, a)


def get_or_create_pair(session: Session, character_a_id: int, character_b_id: int) -> Relationship:
    low, high = canonical_pair(character_a_id, character_b_id)
    relationship = session.exec(
        select(Relationship).where(
            Relationship.character_a_id == low,
            Relationship.character_b_id == high,
        )
    ).first()
    if relationship is None:
        relationship = Relationship(character_a_id=low, character_b_id=high)
        session.add(relationship)
        session.commit()
        session.refresh(relationship)
    return relationship


def _clamp(value: int) -> int:
    return max(0, min(MAX_DIMENSION, value))


def apply_changes(
    session: Session,
    character_a_id: int,
    character_b_id: int,
    changes: dict,
    *,
    log: bool = True,
) -> Relationship:
    relationship = get_or_create_pair(session, character_a_id, character_b_id)
    for dimension in DIMENSIONS:
        if dimension not in changes:
            continue
        current = getattr(relationship, dimension)
        setattr(relationship, dimension, _clamp(current + int(changes[dimension])))
    relationship.updated_at = utcnow()
    if log:
        relationship.last_interaction_at = utcnow()
    session.add(relationship)
    session.commit()
    session.refresh(relationship)
    return relationship


def bump_interaction(
    session: Session,
    a: int,
    b: int,
    changes: dict | None = None,
) -> Relationship:
    if a == b:
        raise ServiceError("Um personagem não se relaciona consigo mesmo.", 400)
    return apply_changes(session, a, b, changes or {}, log=True)


def relationship_between(session: Session, a: int, b: int) -> Relationship | None:
    low, high = canonical_pair(a, b)
    return session.exec(
        select(Relationship).where(
            Relationship.character_a_id == low,
            Relationship.character_b_id == high,
        )
    ).first()


def list_for_character(session: Session, character_id: int) -> list[Relationship]:
    return session.exec(
        select(Relationship).where(
            (Relationship.character_a_id == character_id)
            | (Relationship.character_b_id == character_id)
        )
    ).all()


def pair_other_id(relationship: Relationship, character_id: int) -> int:
    return relationship.character_a_id if relationship.character_b_id == character_id else relationship.character_b_id


def summarize_changes(relationship: Relationship) -> dict[str, int]:
    return {dimension: getattr(relationship, dimension) for dimension in DIMENSIONS}


def add_memory(
    session: Session,
    *,
    owner_character_id: int,
    content: str,
    category: str = "NORMAL",
    kind: str = "shared_experience",
    other_character_id: int | None = None,
    importance: int = 50,
    context: dict | None = None,
    source_event_id: int | None = None,
    dedupe_key: str | None = None,
    occurred_at: datetime | None = None,
) -> Memory:
    content = content.strip()
    if not content:
        raise ServiceError("A memória não pode ficar vazia.", 400)
    if dedupe_key:
        existing = session.exec(
            select(Memory).where(
                Memory.owner_character_id == owner_character_id,
                Memory.dedupe_key == dedupe_key,
            )
        ).first()
        if existing is not None:
            return existing
    memory = Memory(
        owner_character_id=owner_character_id,
        other_character_id=other_character_id,
        category=category,
        kind=kind,
        content=content,
        importance=max(1, min(100, importance)),
        context=context,
        source_event_id=source_event_id,
        dedupe_key=dedupe_key,
        occurred_at=occurred_at or utcnow(),
    )
    session.add(memory)
    session.commit()
    session.refresh(memory)
    return memory


def list_memories(
    session: Session,
    *,
    owner_character_id: int,
    other_character_id: int | None = None,
    category: str | None = None,
    limit: int = 100,
) -> list[Memory]:
    query = select(Memory).where(Memory.owner_character_id == owner_character_id)
    if other_character_id is not None:
        query = query.where(Memory.other_character_id == other_character_id)
    if category:
        query = query.where(Memory.category == category)
    return session.exec(query.order_by(Memory.occurred_at.desc()).limit(limit)).all()


def require_character(session: Session, character_id: int) -> Character:
    character = session.get(Character, character_id)
    if character is None:
        raise ServiceError("Personagem não encontrado.", 404)
    return character