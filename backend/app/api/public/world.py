from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.database.seed_world import advance_world_time_session
from app.database.session import get_session
from app.models import District, Location, SimulationLog, User, WorldState
from app.schemas.common import Listing
from app.schemas.location import (
    DistrictOut,
    LocationOut,
    SimulationAdvanceRequest,
    SimulationLogOut,
    district_out,
    location_out,
)
from app.schemas.world import WorldOut, world_out
from app.services import world_service

router = APIRouter(prefix="/world", tags=["world"])
simulation_router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("", response_model=WorldOut)
def get_world(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return world_out(world_service.get_world(session))


@router.get("/districts", response_model=Listing[DistrictOut])
def list_districts(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    districts = session.exec(select(District).order_by(District.sort_order)).all()
    return Listing(items=[district_out(d) for d in districts])


@router.get("/locations", response_model=Listing[LocationOut])
def list_locations(
    district: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    query = select(Location).order_by(Location.id)
    district_map = {d.id: d for d in session.exec(select(District)).all()}
    if district:
        match = session.exec(select(District).where((District.slug == district) | (District.name == district))).first()
        if match is None:
            return Listing(items=[])
        query = query.where(Location.district_id == match.id)
    locations = session.exec(query).all()
    return Listing(
        items=[
            location_out(loc, district_map[loc.district_id].name if loc.district_id in district_map else "")
            for loc in locations
        ]
    )


@simulation_router.post("/advance", response_model=WorldOut)
def advance_time(
    req: SimulationAdvanceRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    previous_date = world_service.get_world(session).current_date
    state = advance_world_time_session(session, req.minutes)
    if state.current_date != previous_date:
        from app.services.llm_service import generate_posts_for_active_npcs

        session.add(
            SimulationLog(
                kind="npc_posts",
                elapsed_minutes=0,
                summary="Moradores com seguidores publicaram novos posts do dia.",
            )
        )
        session.commit()
        generate_posts_for_active_npcs(session, state.current_date.isoformat())
    return world_out(state)


@simulation_router.get("/logs", response_model=Listing[SimulationLogOut])
def simulation_logs(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    logs = session.exec(select(SimulationLog).order_by(SimulationLog.id.desc()).limit(20)).all()
    return Listing(
        items=[
            SimulationLogOut(
                id=log.id,
                ran_at=log.ran_at.isoformat(),
                kind=log.kind,
                elapsed_minutes=log.elapsed_minutes,
                summary=log.summary,
            )
            for log in logs
        ]
    )


@simulation_router.post("/catchup", response_model=dict)
def run_catchup(
    with_social: bool = True,
    minutes: int | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from app.services.simulation_service import run_catchup as run

    return run(session, with_social=with_social, minutes=minutes)


@router.get("/catchup-report", response_model=Listing[SimulationLogOut])
def catchup_report(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from app.services.simulation_service import latest_report

    logs = latest_report(session)
    return Listing(
        items=[
            SimulationLogOut(
                id=log.id,
                ran_at=log.ran_at.isoformat(),
                kind=log.kind,
                elapsed_minutes=log.elapsed_minutes,
                summary=log.summary,
            )
            for log in logs
        ]
    )
