from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_admin_user
from app.database.session import get_session
from app.domain.errors import ServiceError
from app.models import (
    Character,
    District,
    Job,
    Location,
    Memory,
    Relationship,
    User,
)
from app.schemas.admin import (
    AdminCharacterCreate,
    AdminCharacterUpdate,
    AdminDistrictCreate,
    AdminJobCreate,
    AdminLocationCreate,
    AdminMemoryCreate,
    AdminRelationshipUpdate,
)
from app.schemas.common import Listing
from app.services import relationship_service as rel
from app.services.simulation_service import run_catchup

router = APIRouter(prefix="/admin", tags=["admin"])


def _char_out(c: Character) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "age": c.age,
        "bio": c.bio,
        "profession_label": c.profession_label,
        "is_npc": c.is_npc,
        "discovered_level": c.discovered_level,
        "money": c.money,
        "current_location_id": c.current_location_id,
        "communication_style": c.communication_style,
        "personality": c.personality,
    }


@router.get("/characters", response_model=Listing[dict])
def list_characters(
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(select(Character).order_by(Character.id)).all()
    return Listing(items=[_char_out(c) for c in rows])


@router.post("/characters", response_model=dict, status_code=201)
def create_character(
    req: AdminCharacterCreate,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    character = Character(
        name=req.name.strip(),
        age=req.age,
        bio=req.bio.strip(),
        profession_label=req.profession_label.strip(),
        is_npc=req.is_npc,
        discovered_level=req.discovered_level,
        money=req.money,
        personality={"energy": 0.5, "formality": 0.5, "humor": 0.5, "emoji_usage": 0.4, "tone": "neutro"},
    )
    session.add(character)
    session.commit()
    session.refresh(character)
    return _char_out(character)


@router.patch("/characters/{character_id}", response_model=dict)
def update_character(
    character_id: int,
    req: AdminCharacterUpdate,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    character = session.get(Character, character_id)
    if character is None:
        raise ServiceError("Personagem não encontrado.", 404)
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(character, field, value)
    session.add(character)
    session.commit()
    session.refresh(character)
    return _char_out(character)


def _rel_out(session: Session, r: Relationship) -> dict:
    names = {c.id: c.name for c in session.exec(select(Character)).all()}
    return {
        "id": r.id,
        "character_a_id": r.character_a_id,
        "character_a_name": names.get(r.character_a_id, "?"),
        "character_b_id": r.character_b_id,
        "character_b_name": names.get(r.character_b_id, "?"),
        "familiarity": r.familiarity,
        "friendship": r.friendship,
        "trust": r.trust,
        "romance": r.romance,
        "respect": r.respect,
        "tension": r.tension,
        "last_interaction_at": r.last_interaction_at,
        "updated_at": r.updated_at,
    }


@router.get("/relationships", response_model=Listing[dict])
def list_relationships(
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(select(Relationship).order_by(Relationship.id)).all()
    return Listing(items=[_rel_out(session, r) for r in rows])


@router.patch("/relationships/{relationship_id}", response_model=dict)
def update_relationship(
    relationship_id: int,
    req: AdminRelationshipUpdate,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    relationship = session.get(Relationship, relationship_id)
    if relationship is None:
        raise ServiceError("Relacionamento não encontrado.", 404)
    for field, value in req.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        current = getattr(relationship, field)
        setattr(relationship, field, max(0, min(100, current + value)))
    session.add(relationship)
    session.commit()
    session.refresh(relationship)
    return _rel_out(session, relationship)


@router.delete("/relationships/{relationship_id}", response_model=dict)
def delete_relationship(
    relationship_id: int,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    relationship = session.get(Relationship, relationship_id)
    if relationship is None:
        raise ServiceError("Relacionamento não encontrado.", 404)
    session.delete(relationship)
    session.commit()
    return {"ok": True}


@router.get("/memories", response_model=Listing[dict])
def list_memories(
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(select(Memory).order_by(Memory.id.desc()).limit(200)).all()
    names = {c.id: c.name for c in session.exec(select(Character)).all()}
    return Listing(
        items=[
            {
                "id": m.id,
                "owner_character_id": m.owner_character_id,
                "owner_name": names.get(m.owner_character_id, "?"),
                "other_character_id": m.other_character_id,
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


@router.post("/memories", response_model=dict, status_code=201)
def create_memory(
    req: AdminMemoryCreate,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    memory = rel.add_memory(
        session,
        owner_character_id=req.owner_character_id,
        content=req.content,
        category=req.category,
        kind=req.kind,
        other_character_id=req.other_character_id,
        importance=req.importance,
        context=req.context,
        occurred_at=req.occurred_at,
    )
    return {
        "id": memory.id,
        "owner_character_id": memory.owner_character_id,
        "content": memory.content,
        "category": memory.category,
    }


@router.delete("/memories/{memory_id}", response_model=dict)
def delete_memory(
    memory_id: int,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    memory = session.get(Memory, memory_id)
    if memory is None:
        raise ServiceError("Memória não encontrada.", 404)
    session.delete(memory)
    session.commit()
    return {"ok": True}


def _job_out(session: Session, job: Job) -> dict:
    widgets = {}
    if job.employer_location_id:
        location = session.get(Location, job.employer_location_id)
        widgets["employer_name"] = location.name if location else ""
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "employer_location_id": job.employer_location_id,
        "salary_per_shift": job.salary_per_shift,
        "schedule_template": job.schedule_template or {},
        **widgets,
    }


@router.get("/jobs", response_model=Listing[dict])
def list_jobs(
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(select(Job).order_by(Job.id)).all()
    return Listing(items=[_job_out(session, j) for j in rows])


@router.post("/jobs", response_model=dict, status_code=201)
def create_job(
    req: AdminJobCreate,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    job = Job(
        title=req.title.strip(),
        description=req.description.strip(),
        employer_location_id=req.employer_location_id,
        salary_per_shift=req.salary_per_shift,
        schedule_template=req.schedule_template,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return _job_out(session, job)


@router.patch("/jobs/{job_id}", response_model=dict)
def update_job(
    job_id: int,
    req: AdminJobCreate,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    job = session.get(Job, job_id)
    if job is None:
        raise ServiceError("Vaga não encontrada.", 404)
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    session.add(job)
    session.commit()
    session.refresh(job)
    return _job_out(session, job)


@router.delete("/jobs/{job_id}", response_model=dict)
def delete_job(
    job_id: int,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    job = session.get(Job, job_id)
    if job is None:
        raise ServiceError("Vaga não encontrada.", 404)
    session.delete(job)
    session.commit()
    return {"ok": True}


def _location_out(location: Location) -> dict:
    return {
        "id": location.id,
        "name": location.name,
        "slug": location.slug,
        "district_id": location.district_id,
        "kind": location.kind,
        "description": location.description,
        "is_public": location.is_public,
    }


@router.get("/locations", response_model=Listing[dict])
def list_locations(
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(select(Location).order_by(Location.id)).all()
    return Listing(items=[_location_out(l) for l in rows])


@router.post("/locations", response_model=dict, status_code=201)
def create_location(
    req: AdminLocationCreate,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    if session.get(District, req.district_id) is None:
        raise ServiceError("Distrito inválido.", 400)
    location = Location(
        name=req.name.strip(),
        slug=req.slug.strip(),
        district_id=req.district_id,
        kind=req.kind,
        description=req.description.strip(),
        is_public=req.is_public,
    )
    session.add(location)
    session.commit()
    session.refresh(location)
    return _location_out(location)


@router.delete("/locations/{location_id}", response_model=dict)
def delete_location(
    location_id: int,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    location = session.get(Location, location_id)
    if location is None:
        raise ServiceError("Local não encontrado.", 404)
    session.delete(location)
    session.commit()
    return {"ok": True}


@router.get("/districts", response_model=Listing[dict])
def list_districts(
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    rows = session.exec(select(District).order_by(District.sort_order)).all()
    return Listing(
        items=[
            {"id": d.id, "name": d.name, "slug": d.slug, "description": d.description, "sort_order": d.sort_order}
            for d in rows
        ]
    )


@router.post("/districts", response_model=dict, status_code=201)
def create_district(
    req: AdminDistrictCreate,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    district = District(
        name=req.name.strip(),
        slug=req.slug.strip(),
        description=req.description.strip(),
        sort_order=req.sort_order,
    )
    session.add(district)
    session.commit()
    session.refresh(district)
    return {"id": district.id, "name": district.name}


@router.post("/simulation/routines", response_model=dict)
def run_routines(
    minutes: int | None = None,
    with_social: bool = True,
    user: User = Depends(get_admin_user),
    session: Session = Depends(get_session),
):
    return run_catchup(session, with_social=with_social, minutes=minutes)