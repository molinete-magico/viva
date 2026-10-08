from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta, timezone

from sqlmodel import Session, select

from app.domain import events as de
from app.domain.errors import ServiceError
from app.llm.factory import get_provider
from app.llm.scenes import generate_outcome_summary, generate_scene
from app.models import (
    Character,
    Event,
    EventOutcome,
    EventParticipant,
    EventSession,
    EventTurn,
    FutureHook,
    Location,
    Notification,
    WorldState,
)
from app.models.base import utcnow
from app.schemas.events import CreateEventRequest
from app.services import milestone_service, relationship_service as rel

_SCENE_MODEL = "quick"


def _load_event(session: Session, event_id: int) -> Event:
    event = session.get(Event, event_id)
    if event is None:
        raise ServiceError("Evento não encontrado.", 404)
    return event


def _load_session(session: Session, session_id: int) -> EventSession:
    event_session = session.get(EventSession, session_id)
    if event_session is None:
        raise ServiceError("Sessão de evento não encontrada.", 404)
    return event_session


def _world_chronology(session: Session) -> dict:
    state = session.get(WorldState, 1)
    if state is None:
        state = WorldState(current_date=utcnow().date(), current_time="08:00")
    day_names = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    return {
        "day_name": day_names[state.current_date.weekday()],
        "date": state.current_date.isoformat(),
        "time": state.current_time,
    }


def _notify(session: Session, character_id: int, type: str, payload: dict) -> None:
    session.add(Notification(character_id=character_id, type=type, payload=payload))


def _npc_participants(session: Session, event: Event, exclude_id: int | None = None) -> list[Character]:
    ids = session.exec(
        select(EventParticipant.character_id).where(
            EventParticipant.event_id == event.id,
            EventParticipant.status.in_(["JOINED", "ACCEPTED", "INVITED"]),
        )
    ).all()
    char_ids = [row[0] if isinstance(row, tuple) else row for row in ids]
    if exclude_id is not None and exclude_id in char_ids:
        char_ids.remove(exclude_id)
    if event.host_character_id and event.host_character_id not in char_ids:
        char_ids.append(event.host_character_id)
    if not char_ids:
        return []
    chars = session.exec(select(Character).where(Character.id.in_(char_ids))).all()
    npcs = [c for c in chars if c.is_npc]
    order = {c.id: i for i, c in enumerate(chars)}
    return sorted(npcs, key=lambda c: order.get(c.id, 0))


def _scene_participant_names(participants: list[Character], player_name: str) -> list[str]:
    names = [c.name for c in participants]
    others = [n for n in names if n != player_name]
    slots = others
    if len(slots) < 2:
        slots = slots + ["os presentes"]
    return slots[:3]


def create_event(session: Session, host: Character, req: CreateEventRequest) -> Event:
    location = session.get(Location, req.location_id)
    if location is None:
        raise ServiceError("Local do evento não existe.", 400)
    invitee_ids: list[int] = []
    seen_conversations: set[int] = set()
    for conversation_id in req.invite_conversation_ids:
        if conversation_id in seen_conversations:
            continue
        seen_conversations.add(conversation_id)
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise ServiceError(f"Conversa #{conversation_id} não existe.", 400)
        if host.id not in (conversation.character_a_id, conversation.character_b_id):
            raise ServiceError(f"Você não participa da conversa #{conversation_id}.", 403)
        target_id = (
            conversation.character_b_id
            if conversation.character_a_id == host.id
            else conversation.character_a_id
        )
        target = session.get(Character, target_id)
        if target is None:
            raise ServiceError(f"O personagem da conversa #{conversation_id} não existe.", 400)
        if target.id == host.id:
            continue
        if target.id not in invitee_ids:
            invitee_ids.append(target.id)

    event = Event(
        title=req.title.strip(),
        description=req.description.strip(),
        location_id=req.location_id,
        host_character_id=host.id,
        created_by="system" if host.is_npc else "player",
        scheduled_at=None,
        kind=req.kind,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    host_participant = EventParticipant(
        event_id=event.id,
        character_id=host.id,
        status=de.PARTICIPANT_JOINED,
        responded_at=utcnow(),
        joined_at=utcnow(),
    )
    session.add(host_participant)
    for invitee_id in invitee_ids:
        session.add(
            EventParticipant(
                event_id=event.id,
                character_id=invitee_id,
                status=de.PARTICIPANT_INVITED,
            )
        )
    session.commit()
    player_invitees = session.exec(
        select(Character).where(Character.id.in_(invitee_ids), Character.user_id.is_not(None))
    ).all() if req.invitees else []
    world = _world_chronology(session)
    for player in player_invitees:
        _notify(
            session,
            player.id,
            "EVENT_INVITE",
            {
                "event_id": event.id,
                "title": event.title,
                "location_name": location.name,
                "scheduled_at": None,
                "chronology": f"{world['day_name']} {world['date']} {world['time']}",
            },
        )
    session.commit()
    session.refresh(event)
    return event


def _participant(session: Session, event_id: int, character_id: int) -> EventParticipant | None:
    return session.exec(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.character_id == character_id,
        )
    ).first()


def rsvp(session: Session, character: Character, event_id: int, accept: bool) -> EventParticipant:
    event = _load_event(session, event_id)
    if event.status in (de.EVENT_COMPLETED, de.EVENT_CANCELLED):
        raise ServiceError("Esse evento já foi encerrado ou cancelado.", 409)
    participant = _participant(session, event_id, character.id)
    if participant is None:
        raise ServiceError("Você ainda não foi convidado para este evento.", 403)
    next_status = de.transition_participant(participant.status, "accept" if accept else "decline")
    participant.status = next_status
    participant.responded_at = utcnow()
    session.add(participant)
    session.commit()
    session.refresh(participant)
    return participant


def cancel_event(session: Session, actor: Character, event_id: int, reason: str) -> Event:
    event = _load_event(session, event_id)
    if event.host_character_id != actor.id and not actor.is_npc and actor.user_id is not None:
        raise ServiceError("Só quem organizou pode cancelar o evento.", 403)
    event.status = de.transition_event(event.status, "cancel")
    event.cancel_reason = (reason or "").strip()[:500]
    session.add(event)
    session.commit()
    joined = session.exec(
        select(Character).where(
            Character.id.in_(
                select(EventParticipant.character_id).where(
                    EventParticipant.event_id == event_id,
                    EventParticipant.status.in_([de.PARTICIPANT_JOINED, de.PARTICIPANT_ACCEPTED]),
                )
            ),
            Character.user_id.is_not(None),
        )
    ).all()
    for player in joined:
        _notify(
            session,
            player.id,
            "EVENT_CANCELLED",
            {"event_id": event.id, "title": event.title, "reason": event.cancel_reason},
        )
    session.commit()
    session.refresh(event)
    return event


def _assert_playable(session: Session, character: Character, event: Event) -> EventParticipant:
    if event.status not in (de.EVENT_SCHEDULED, de.EVENT_OPEN, de.EVENT_ACTIVE):
        raise ServiceError("Este evento não está disponível agora.", 409)
    participant = _participant(session, event.id, character.id)
    if participant is None or participant.status not in (
        de.PARTICIPANT_ACCEPTED,
        de.PARTICIPANT_JOINED,
    ):
        raise ServiceError("Confirme presença no evento antes de entrar.", 403)
    return participant


def _make_turn(
    session: Session,
    event_session: EventSession,
    *,
    turn_index: int,
    player_action_id: str | None,
    player_action_label: str | None,
    scene: dict,
) -> EventTurn:
    turn = EventTurn(
        session_id=event_session.id,
        turn_index=turn_index,
        narrative=scene.get("narrative", "")[: de.MAX_TURN_LENGTH],
        dialogue=scene.get("dialogue", [])[:3],
        available_actions=scene.get("actions", [])[: de.MAX_EVENT_ACTIONS],
        player_action_id=player_action_id,
        player_action_label=player_action_label,
    )
    session.add(turn)
    event_session.turn_count = turn_index + 1
    event_session.last_activity_at = utcnow()
    session.add(event_session)
    session.commit()
    session.refresh(turn)
    return turn


def start_or_resume_session(session: Session, character: Character, event_id: int) -> EventSession:
    event = _load_event(session, event_id)
    _assert_playable(session, character, event)
    existing = session.exec(
        select(EventSession).where(
            EventSession.event_id == event_id,
            EventSession.player_character_id == character.id,
        )
    ).first()
    if existing is not None:
        if existing.status == de.SESSION_ACTIVE:
            return existing
        if existing.status == de.SESSION_COMPLETED:
            raise ServiceError("Você já viveu os acontecimentos deste evento.", 409)
        raise ServiceError("Sessão encerrada. Volte para participar de um novo evento.", 409)
    participant = _assert_playable(session, character, event)
    participant.status = de.PARTICIPANT_JOINED
    participant.joined_at = utcnow()
    session.add(participant)
    event_session = EventSession(event_id=event.id, player_character_id=character.id)
    if event.status not in (de.EVENT_ACTIVE,):
        event.status = de.transition_event(event.status, "start")
    session.add(event_session)
    session.add(event)
    session.commit()
    session.refresh(event_session)
    scene = _scene(session, character, event, event_session, last_action=None)
    _make_turn(session, event_session, turn_index=0, player_action_id=None, player_action_label=None, scene=scene)
    session.refresh(event_session)
    return event_session


def _scene(
    session: Session,
    character: Character,
    event: Event,
    event_session: EventSession,
    *,
    last_action: str | None,
    free_text_action: str | None = None,
) -> dict:
    participants = _npc_participants(session, event, exclude_id=character.id)
    location = session.get(Location, event.location_id) or Location(name="na cidade")
    world = _world_chronology(session)
    narrative_rows = session.exec(
        select(EventTurn.narrative)
        .where(EventTurn.session_id == event_session.id)
        .order_by(EventTurn.turn_index.desc())
        .limit(8)
    ).all()
    narrative_so_far = [row[0] for row in narrative_rows][::-1]
    chronology = f"{world['day_name']}, dia {world['date']}"
    host = session.get(Character, event.host_character_id) if event.host_character_id else None
    scene = asyncio.run(
        generate_scene(
            get_provider(),
            event_title=event.title,
            location_name=location.name,
            host_name=host.name if host else "o anfitrião",
            participants=_scene_participant_names(participants, character.name),
            player_name=character.name,
            chronology=chronology,
            narrative_so_far=narrative_so_far,
            last_action=last_action,
            free_text_action=free_text_action,
            turn_index=event_session.turn_count,
        )
    )
    return scene


def session_state(session: Session, character: Character, session_id: int) -> EventSession:
    event_session = _load_session(session, session_id)
    if event_session.player_character_id != character.id:
        raise ServiceError("Esta sessão não pertence ao seu personagem.", 403)
    return event_session


def last_turn(session: Session, event_session: EventSession) -> EventTurn | None:
    return session.exec(
        select(EventTurn)
        .where(EventTurn.session_id == event_session.id)
        .order_by(EventTurn.turn_index.desc())
    ).first()


def perform_action(
    session: Session,
    character: Character,
    session_id: int,
    action_id: str | None = None,
    free_text: str | None = None,
) -> EventTurn:
    event_session = session_state(session, character, session_id)
    if event_session.status != de.SESSION_ACTIVE:
        raise ServiceError("Esta sessão não está ativa.", 409)
    if event_session.turn_count >= de.MAX_TURNS:
        raise ServiceError("Este evento acabou de cansar; encerre a sessão para colher os efeitos.", 409)
    event = _load_event(session, event_session.event_id)
    turn = last_turn(session, event_session)
    if turn is None:
        raise ServiceError("Sessão ainda sem cena inicial.", 409)
    chosen = next((a for a in turn.available_actions if a.get("id") == action_id), None) if action_id else None
    if chosen is None and not free_text:
        raise ServiceError("Escolha uma ação ou descreva o que deseja fazer.", 400)
    # Ação livre é intenção narrativa. O LLM pode interpretar a intenção,
    # mas não recebe autoridade para aplicar consequências de domínio.
    effects = (chosen.get("effects") if chosen else {}) or {}
    effective_label = chosen.get("label") if chosen else free_text.strip()[:1000]

    money = effects.get("money")
    if money:
        character.money = round((character.money or 0) + float(money), 2)
        session.add(character)

    mem_text = effects.get("memory")
    if mem_text:
        targets = _npc_participants(session, event, exclude_id=character.id)
        rel.add_memory(
            session,
            owner_character_id=character.id,
            other_character_id=targets[0].id if targets else None,
            content=str(mem_text)[:2000],
            category="EVENT",
            kind="event_memory",
            importance=int(effects.get("memory_importance", 30)),
            source_event_id=event.id,
            dedupe_key=f"event-{event.id}-turn-{turn.turn_index}",
        )

    npc_targets = _npc_participants(session, event, exclude_id=character.id)
    action_effects = effects.get("relationship")
    if action_effects and npc_targets:
        target_id = int(action_effects.get("character_id") or npc_targets[0].id)
        target = session.get(Character, target_id)
        if target is None or not target.is_npc:
            target_id = npc_targets[0].id
        deltas = {k: v for k, v in action_effects.items() if k in de.DIMENSIONS}
        if deltas:
            rel.apply_changes(session, character.id, target_id, deltas, log=True)

    scene = _scene(
        session,
        character,
        event,
        event_session,
        last_action=chosen.get("label") if chosen else None,
        free_text_action=free_text,
    )
    session.add(character)
    new_turn = _make_turn(
        session,
        event_session,
        turn_index=event_session.turn_count,
        player_action_id=action_id or "free_text",
        player_action_label=effective_label,
        scene=scene,
    )

    # O narrador pode declarar que a situação chegou naturalmente ao fim.
    # Isso não concede autoridade sobre efeitos: end_session continua sendo
    # o único caminho que materializa memória, milestone, outcome e future hooks.
    flags = scene.get("_flags") if isinstance(scene.get("_flags"), dict) else {}
    natural_end = bool(
        flags.get("complete")
        or flags.get("event_complete")
        or flags.get("session_complete")
    )
    if natural_end and event_session.status == de.SESSION_ACTIVE:
        end_session(session, character, session_id)

    return new_turn


def end_session(session: Session, character: Character, session_id: int, summary: str | None = None) -> EventOutcome:
    event_session = session_state(session, character, session_id)
    if event_session.status != de.SESSION_ACTIVE:
        outcome = session.exec(
            select(EventOutcome).where(EventOutcome.session_id == session_id)
        ).first()
        if outcome is not None:
            return outcome
        raise ServiceError("Esta sessão não está ativa para ser encerrada.", 409)
    event = _load_event(session, event_session.event_id)
    turns = session.exec(
        select(EventTurn).where(EventTurn.session_id == session_id).order_by(EventTurn.turn_index)
    ).all()
    npc_ids = [p.id for p in _npc_participants(session, event, exclude_id=character.id)]
    narrative_so_far = [t.narrative for t in turns]

    if not summary:
        summary = asyncio.run(
            generate_outcome_summary(
                get_provider(),
                event_title=event.title,
                player_name=character.name,
                participant_names=_scene_participant_names(
                    _npc_participants(session, event, exclude_id=character.id), character.name
                ),
                narrative_so_far=narrative_so_far,
            )
        )

    memories: list[dict] = []
    for npc_id in npc_ids[:2]:
        other = session.get(Character, npc_id)
        if other is None:
            continue
        memory = rel.add_memory(
            session,
            owner_character_id=character.id,
            other_character_id=npc_id,
            content=(summary[:1800] or f"O dia em que passamos por {event.title} juntos."),
            category="EVENT",
            kind="event_memory",
            importance=40,
            context={"event_id": event.id, "title": event.title},
            source_event_id=event.id,
            dedupe_key=f"event-{event.id}-{character.id}-{npc_id}",
        )
        # A experiência também pertence à memória do NPC. Isso permite que
        # encontros futuros reconheçam o passado sem depender de o jogador
        # voltar a mencionar o evento.
        npc_memory = rel.add_memory(
            session,
            owner_character_id=npc_id,
            other_character_id=character.id,
            content=(f"Passei por {event.title} com {character.name}. {summary[:1200]}").strip(),
            category="EVENT",
            kind="shared_experience",
            importance=35,
            context={"event_id": event.id, "title": event.title},
            source_event_id=event.id,
            dedupe_key=f"event-{event.id}-{npc_id}-{character.id}",
        )
        memories.append({
            "character_id": npc_id,
            "name": other.name,
            "memory_id": memory.id,
            "npc_memory_id": npc_memory.id,
        })
    if not memories:
        memory = rel.add_memory(
            session,
            owner_character_id=character.id,
            content=(summary[:1800] or f"O que rolou lá em {event.title}."),
            category="EVENT",
            kind="event_memory",
            importance=30,
            context={"event_id": event.id, "title": event.title},
            source_event_id=event.id,
            dedupe_key=f"event-{event.id}-{character.id}",
        )
        memories.append({"character_id": None, "name": "", "memory_id": memory.id})

    event_session.status = de.transition_session(event_session.status, "complete")
    event_session.ended_at = utcnow()
    session.add(event_session)
    if event.status in (de.EVENT_ACTIVE, de.EVENT_OPEN, de.EVENT_SCHEDULED):
        event.status = de.transition_event(event.status, "complete")
        session.add(event)

    # Um evento significativo pode continuar ecoando depois que termina.
    # No máximo um gancho pendente de DM por personagem-alvo evita spam.
    future_hooks: list[dict] = []
    for npc_id in npc_ids[:2]:
        pending = session.exec(
            select(FutureHook).where(
                FutureHook.target_character_id == character.id,
                FutureHook.status == "PENDING",
                FutureHook.kind == "dm_message",
            )
        ).first()
        if pending is not None:
            continue
        npc = session.get(Character, npc_id)
        if npc is None:
            continue
        world_state = session.get(WorldState, 1)
        base_world_dt = (
            datetime.combine(
                world_state.current_date,
                time.fromisoformat(world_state.current_time),
                tzinfo=timezone.utc,
            )
            if world_state is not None
            else utcnow()
        )
        hook = FutureHook(
            source_type="event",
            source_id=event.id,
            target_character_id=character.id,
            kind="dm_message",
            payload={
                "sender_character_id": npc.id,
                "message": f"Ei. Fiquei pensando em {event.title}. Foi bom você ter ido.",
            },
            due_at=base_world_dt + timedelta(days=1),
        )
        session.add(hook)
        session.flush()
        future_hooks.append({"id": hook.id, "kind": hook.kind, "sender_id": npc.id})

    outcome = EventOutcome(
        session_id=session_id,
        summary=summary[:4000],
        relationship_changes=[],
        memories=memories,
        social_effects=[],
        future_hooks=future_hooks,
        applied_at=utcnow(),
    )
    session.add(outcome)
    milestone_service.record_progress(session, "EVENT_PARTICIPATION", 1)
    _notify(
        session,
        character.id,
        "EVENT_RESULT",
        {
            "event_id": event.id,
            "title": event.title,
            "summary": summary[:200],
            "session_id": session_id,
        },
    )
    session.commit()
    session.refresh(outcome)
    return outcome


def abandon_session(session: Session, character: Character, session_id: int) -> EventSession:
    event_session = session_state(session, character, session_id)
    if event_session.status != de.SESSION_ACTIVE:
        raise ServiceError("Esta sessão não está ativa.", 409)
    event = _load_event(session, event_session.event_id)
    event_session.status = de.transition_session(event_session.status, "abandon")
    event_session.ended_at = utcnow()
    session.add(event_session)
    participant = _participant(session, event.id, character.id)
    if participant is not None:
        participant.status = de.PARTICIPANT_WITHDREW
        session.add(participant)
    still_active = session.exec(
        select(EventSession).where(
            EventSession.event_id == event.id,
            EventSession.status == de.SESSION_ACTIVE,
        )
    ).first()
    if still_active is None and event.status == de.EVENT_ACTIVE:
        event.status = de.EVENT_OPEN
        session.add(event)
    session.commit()
    session.refresh(event_session)
    return event_session


def get_outcome(session: Session, character: Character, session_id: int) -> EventOutcome | None:
    event_session = session_state(session, character, session_id)
    return session.exec(
        select(EventOutcome).where(EventOutcome.session_id == event_session.id)
    ).first()


def check_open_events(session: Session, current: datetime) -> None:
    events = session.exec(
        select(Event).where(
            Event.status == de.EVENT_SCHEDULED,
            Event.scheduled_at <= current,
        )
    ).all()
    changed = 0
    for event in events:
        event.status = de.EVENT_OPEN
        session.add(event)
        changed += 1
    if changed:
        session.commit()


def recover_stale_event_sessions(session: Session, *, max_idle_minutes: int = 24 * 60) -> int:
    """Sessões de evento dormindo além do limite são arquivadas (abandon).

    O jogador sai (participante WITHDREW) e o evento volta a OPEN se não houver
    outra sessão ativa — mesma regra do abandono manual. Rodado no catch-up.
    """
    cutoff = utcnow() - timedelta(minutes=max_idle_minutes)
    stale = session.exec(
        select(EventSession).where(
            EventSession.status == de.SESSION_ACTIVE,
            EventSession.last_activity_at < cutoff,
        )
    ).all()
    if not stale:
        return 0
    resolved = 0
    for event_session in stale:
        event = session.get(Event, event_session.event_id)
        event_session.status = de.SESSION_ABANDONED
        event_session.ended_at = utcnow()
        session.add(event_session)
        participant = _participant(session, event.id, event_session.player_character_id)
        if participant is not None and participant.status == de.PARTICIPANT_JOINED:
            participant.status = de.PARTICIPANT_WITHDREW
            session.add(participant)
        if event is not None and event.status == de.EVENT_ACTIVE:
            still_active = session.exec(
                select(EventSession).where(
                    EventSession.event_id == event.id,
                    EventSession.status == de.SESSION_ACTIVE,
                )
            ).first()
            if still_active is None:
                event.status = de.EVENT_OPEN
                session.add(event)
        resolved += 1
    session.commit()
    return resolved