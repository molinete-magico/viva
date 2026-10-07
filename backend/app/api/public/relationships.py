from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.database.session import get_session
from app.models import Character, User
from app.schemas.common import Listing
from app.services import character_service, milestone_service, relationship_service as rel

router = APIRouter(tags=["relationships"])
milestones_router = APIRouter(prefix="/milestones", tags=["milestones"])


def _relationship_out(session: Session, relationship: rel.Relationship, viewer_id: int | None) -> dict:
    other_id = rel.pair_other_id(relationship, viewer_id) if viewer_id is not None else relationship.character_b_id
    other = session.get(Character, other_id)
    return {
        "id": relationship.id,
        "character_a_id": relationship.character_a_id,
        "character_b_id": relationship.character_b_id,
        "other_character_id": other_id,
        "other_name": other.name if other else "?",
        "other_is_npc": other.is_npc if other else True,
        "familiarity": relationship.familiarity,
        "friendship": relationship.friendship,
        "trust": relationship.trust,
        "romance": relationship.romance,
        "respect": relationship.respect,
        "tension": relationship.tension,
        "last_interaction_at": relationship.last_interaction_at,
        "updated_at": relationship.updated_at,
    }


@router.get("/relationships", response_model=Listing[dict])
def list_relationships(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    rows = rel.list_for_character(session, character.id)
    items = [_relationship_out(session, r, character.id) for r in rows]
    items.sort(key=lambda r: -(r["familiarity"] + r["friendship"] + r["trust"]))
    return Listing(items=items)


@router.get("/characters/{character_id}/relationship", response_model=dict)
def character_relationship(
    character_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    if character.id == character_id:
        return {"id": None}
    relationship = rel.relationship_between(session, character.id, character_id)
    if relationship is None:
        return {"id": None}
    return _relationship_out(session, relationship, character.id)


@router.get("/characters/{character_id}/memories", response_model=Listing[dict])
def character_memories(
    character_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    rows = rel.list_memories(
        session,
        owner_character_id=character.id,
        other_character_id=None if character_id == character.id else character_id,
    )
    characters = {c.id: c.name for c in session.exec(select(Character)).all()}
    return Listing(
        items=[
            {
                "id": m.id,
                "other_character_id": m.other_character_id,
                "other_name": characters.get(m.other_character_id, ""),
                "category": m.category,
                "kind": m.kind,
                "content": m.content,
                "importance": m.importance,
                "occurred_at": m.occurred_at,
                "context": m.context or {},
            }
            for m in rows
        ]
    )


@router.get("/milestones", response_model=Listing[dict])
def list_milestones(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return Listing(items=milestone_service.list_milestones(session))


@milestones_router.post("/{key}/claim", response_model=dict)
def claim_milestone(
    key: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    return milestone_service.claim(session, key.upper(), owner=character)