from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.database.session import get_session
from app.models import (
    Event,
    EventOutcome,
    EventParticipant,
    EventSession,
    EventTurn,
    User,
)
from app.schemas.common import Listing
from app.schemas.events import (
    ActionRequest,
    CancelEventRequest,
    CreateEventRequest,
    EventDetailOut,
    EventOut,
    EventParticipantOut,
    OutcomeOut,
    RSVPRequest,
    SessionStateOut,
    SessionSummaryOut,
    TurnOut,
)
from app.services import character_service, event_service

router = APIRouter(prefix="/events", tags=["events"])


def _to_out(session: Session, event: Event, viewer_id: int | None, counts: dict, my: dict) -> EventOut:
    from app.models import Character

    host = session.get(Character, event.host_character_id) if event.host_character_id else None
    return EventOut(
        id=event.id,
        title=event.title,
        description=event.description,
        status=event.status,
        kind=event.kind,
        host_character_id=event.host_character_id,
        host_name=host.name if host else "",
        participant_count=counts.get(event.id, 0),
        my_status=my.get(event.id),
        cancel_reason=event.cancel_reason,
    )


def _turn_out(turn: EventTurn) -> TurnOut:
    return TurnOut(
        id=turn.id,
        turn_index=turn.turn_index,
        narrative=turn.narrative,
        dialogue=turn.dialogue or [],
        available_actions=turn.available_actions or [],
        player_action_id=turn.player_action_id,
        player_action_label=turn.player_action_label,
        created_at=turn.created_at,
    )


def _session_state(session: Session, event_session: EventSession) -> SessionStateOut:
    turns = session.exec(
        select(EventTurn)
        .where(EventTurn.session_id == event_session.id)
        .order_by(EventTurn.turn_index)
    ).all()
    outcome = session.exec(
        select(EventOutcome).where(EventOutcome.session_id == event_session.id)
    ).first()
    return SessionStateOut(
        session=SessionSummaryOut(
            id=event_session.id,
            event_id=event_session.event_id,
            status=event_session.status,
            turn_count=event_session.turn_count,
            resume_count=event_session.resume_count,
            started_at=event_session.started_at,
            ended_at=event_session.ended_at,
            last_activity_at=event_session.last_activity_at,
        ),
        turns=[_turn_out(t) for t in turns],
        can_act=event_session.status == "ACTIVE",
        outcome_id=outcome.id if outcome else None,
    )


@router.get("", response_model=Listing[EventOut])
def list_events(
    mine: bool = False,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    viewer_id = user.active_character_id
    query = select(Event).order_by(Event.created_at.desc()).limit(200)
    events = session.exec(query).all()
    if not events:
        return Listing(items=[])
    event_ids = [e.id for e in events]
    rows = session.exec(
        select(EventParticipant.event_id, func.count(EventParticipant.id))
        .where(EventParticipant.event_id.in_(event_ids))
        .group_by(EventParticipant.event_id)
    ).all()
    counts = {row[0]: row[1] for row in rows}
    my: dict[int, str] = {}
    if viewer_id is not None:
        mine_rows = session.exec(
            select(EventParticipant).where(
                EventParticipant.event_id.in_(event_ids),
                EventParticipant.character_id == viewer_id,
            )
        ).all()
        my = {p.event_id: p.status for p in mine_rows}
    items = [_to_out(session, e, viewer_id, counts, my) for e in events]
    if mine and viewer_id is not None:
        items = [i for i in items if i.my_status is not None]
    return Listing(items=items)


@router.post("", response_model=EventOut, status_code=201)
def create_event(
    req: CreateEventRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    event = event_service.create_event(session, character, req)
    return _to_out(session, event, character.id, {}, {event.id: "JOINED"})


@router.get("/{event_id}", response_model=EventDetailOut)
def get_event(
    event_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    event = event_service._load_event(session, event_id)
    counts: dict[int, int] = {}
    my: dict[int, str] = {}
    if user.active_character_id is not None:
        count = session.exec(
            select(func.count(EventParticipant.id)).where(EventParticipant.event_id == event_id)
        ).one()
        counts[event_id] = count
        participant = event_service._participant(session, event_id, user.active_character_id)
        my[event_id] = participant.status if participant else None
    from app.models import Character

    characters = {c.id: c for c in session.exec(select(Character)).all()}
    participant_rows = session.exec(
        select(EventParticipant).where(EventParticipant.event_id == event_id)
    ).all()
    participants = [
        EventParticipantOut(
            character_id=p.character_id,
            name=characters[p.character_id].name if p.character_id in characters else "?",
            status=p.status,
            is_npc=characters[p.character_id].is_npc if p.character_id in characters else True,
        )
        for p in participant_rows
    ]
    base = _to_out(session, event, user.active_character_id, counts, my)
    return EventDetailOut(
        **base.model_dump(),
        participants=participants,
        am_host=event.host_character_id is not None and event.host_character_id == user.active_character_id,
    )


@router.post("/{event_id}/rsvp", response_model=EventDetailOut)
def rsvp_event(
    event_id: int,
    req: RSVPRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    event_service.rsvp(session, character, event_id, req.accept)
    event = event_service._load_event(session, event_id)
    return get_event(event_id, user, session)


@router.post("/{event_id}/cancel", response_model=EventOut)
def cancel_event(
    event_id: int,
    req: CancelEventRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    event = event_service.cancel_event(session, character, event_id, req.reason)
    return _to_out(session, event, character.id, {}, {})


@router.post("/{event_id}/sessions", response_model=SessionStateOut)
def start_session(
    event_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    event_session = event_service.start_or_resume_session(session, character, event_id)
    return _session_state(session, event_session)


@router.get("/{event_id}/sessions", response_model=Listing[SessionSummaryOut])
def list_my_sessions(
    event_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    rows = session.exec(
        select(EventSession).where(
            EventSession.event_id == event_id,
            EventSession.player_character_id == character.id,
        )
    ).all()
    return Listing(
        items=[
            SessionSummaryOut(
                id=r.id,
                event_id=r.event_id,
                status=r.status,
                turn_count=r.turn_count,
                resume_count=r.resume_count,
                started_at=r.started_at,
                ended_at=r.ended_at,
                last_activity_at=r.last_activity_at,
            )
            for r in rows
        ]
    )


@router.get("/sessions/{session_id}", response_model=SessionStateOut)
def get_event_session(
    session_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    event_session = event_service.session_state(session, character, session_id)
    return _session_state(session, event_session)


@router.post("/sessions/{session_id}/actions", response_model=TurnOut)
def perform_action(
    session_id: int,
    req: ActionRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    turn = event_service.perform_action(session, character, session_id, req.action_id, req.free_text)
    return _turn_out(turn)


@router.post("/sessions/{session_id}/end", response_model=OutcomeOut)
def end_session(
    session_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    outcome = event_service.end_session(session, character, session_id)
    return OutcomeOut(
        id=outcome.id,
        session_id=outcome.session_id,
        summary=outcome.summary,
        relationship_changes=outcome.relationship_changes or [],
        memories=outcome.memories or [],
        social_effects=outcome.social_effects or [],
        future_hooks=outcome.future_hooks or [],
        applied_at=outcome.applied_at,
    )


@router.post("/sessions/{session_id}/abandon", response_model=SessionSummaryOut)
def abandon_session(
    session_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    event_session = event_service.abandon_session(session, character, session_id)
    return SessionSummaryOut(
        id=event_session.id,
        event_id=event_session.event_id,
        status=event_session.status,
        turn_count=event_session.turn_count,
        resume_count=event_session.resume_count,
        started_at=event_session.started_at,
        ended_at=event_session.ended_at,
        last_activity_at=event_session.last_activity_at,
    )


@router.get("/sessions/{session_id}/outcome", response_model=OutcomeOut)
def get_outcome(
    session_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    character = character_service.require_active_character(session, user)
    outcome = event_service.get_outcome(session, character, session_id)
    if outcome is None:
        from app.domain.errors import ServiceError

        raise ServiceError("Sessão ainda sem desfecho.", 404)
    return OutcomeOut(
        id=outcome.id,
        session_id=outcome.session_id,
        summary=outcome.summary,
        relationship_changes=outcome.relationship_changes or [],
        memories=outcome.memories or [],
        social_effects=outcome.social_effects or [],
        future_hooks=outcome.future_hooks or [],
        applied_at=outcome.applied_at,
    )