from __future__ import annotations

import logging
from datetime import datetime, time, timezone

from sqlmodel import Session, select

from app.models import Character, FutureHook, SimulationLog, WorldState
from app.models.base import utcnow

logger = logging.getLogger("viva.simulation")

MAX_CATCHUP_MINUTES = 1440


def compute_elapsed_minutes(session: Session) -> int:
    state = session.get(WorldState, 1)
    if state is None or state.last_simulated_at is None:
        return 0
    elapsed = (utcnow() - state.last_simulated_at).total_seconds() / 60
    return max(15, min(MAX_CATCHUP_MINUTES, int(elapsed)))


def _combine(state: WorldState) -> datetime:
    return datetime.combine(state.current_date, time.fromisoformat(state.current_time), tzinfo=timezone.utc)


def process_due_future_hooks(session: Session, *, simulated_now: datetime | None = None) -> list[str]:
    """Entrega consequências sociais que amadureceram enquanto o app estava fechado."""
    from app.services.messaging_service import send_npc_initiative

    now = simulated_now or utcnow()
    hooks = session.exec(
        select(FutureHook).where(
            FutureHook.status == "PENDING",
            FutureHook.due_at.is_not(None),
            FutureHook.due_at <= now,
        ).order_by(FutureHook.due_at.asc()).limit(20)
    ).all()
    delivered: list[str] = []
    for hook in hooks:
        target = session.get(Character, hook.target_character_id)
        sender_id = (hook.payload or {}).get("sender_character_id")
        sender = session.get(Character, sender_id) if sender_id else None
        message = str((hook.payload or {}).get("message") or "").strip()
        if target is None or sender is None or not sender.is_npc or not message:
            hook.status = "EXPIRED"
            session.add(hook)
            continue
        try:
            send_npc_initiative(session, sender, target, message)
            hook.status = "CONSUMED"
            session.add(hook)
            delivered.append(f"{sender.name} mandou uma mensagem")
        except Exception:
            logger.exception("future hook %s failed", hook.id)
    if hooks:
        session.commit()
    return delivered

def run_catchup(session: Session, *, with_social: bool = True, minutes: int | None = None) -> dict:
    from app.database.seed_world import advance_world_time_session

    state = session.get(WorldState, 1)
    if state is None:
        return {"skipped": "sem relógio do mundo", "elapsed_minutes": 0}
    elapsed = minutes if minutes is not None and minutes > 0 else compute_elapsed_minutes(session)
    if elapsed <= 0:
        return {"skipped": "sem tempo acumulado", "elapsed_minutes": 0}

    from_dt = _combine(state)
    state = advance_world_time_session(session, elapsed)
    until_dt = _combine(state)

    from app.services.economy_service import process_shifts_and_routines

    economy = process_shifts_and_routines(session, from_dt, until_dt)

    from app.services.event_service import check_open_events, recover_stale_event_sessions
    from app.services.messaging_service import idle_conversation_sessions

    check_open_events(session, until_dt)
    stale_sessions = recover_stale_event_sessions(session)
    idle_sessions = idle_conversation_sessions(session)
    future_social = process_due_future_hooks(session, simulated_now=until_dt)

    social: list[str] = []
    if with_social:
        # O mundo agora é simulado em fatias de 90 minutos. Isso é importante:
        # um retorno depois de oito horas não pode parecer um único "pulso" artificial.
        from app.services.autonomy_service import simulate_social_life
        from app.services.social_arc_service import update_social_arcs, advance_character_goals, propagate_rumors, advance_social_intentions
        from app.services.autonomous_world_service import run_social_dynamics
        from app.services.city_life_service import run_city_life
        from app.services.social_service import npc_social_reactions

        try:
            life = simulate_social_life(session, from_dt, until_dt)
            if life["interactions"]:
                social.append(f"{life['interactions']} encontros entre moradores")
            if life["posts"]:
                social.append(f"{life['posts']} posts espontâneos")
            if life["comments"] or life["likes"]:
                social.append(f"{life['comments']} comentários e {life['likes']} curtidas entre NPCs")
            if life["activities"]:
                social.append(f"{life['activities']} atividade(s) espontânea(s) surgiram na cidade")
            if life["proactive_dms"]:
                social.append(f"{life['proactive_dms']} morador(es) procuraram alguém por iniciativa própria")

            arc_transitions, arc_highlights = update_social_arcs(session, until_dt)
            intent_actions, intent_highlights = advance_social_intentions(session, until_dt)
            goal_progress, goal_highlights = advance_character_goals(session, until_dt)
            rumors_spread, rumor_highlights = propagate_rumors(session, until_dt)
            if arc_transitions:
                social.append(f"{arc_transitions} mudança(s) de arco social")
            if intent_actions:
                social.append(f"{intent_actions} iniciativa(s) social(is) aconteceram")
            if goal_progress:
                social.append(f"{goal_progress} objetivo(s) social(is) avançaram")
            if rumors_spread:
                social.append(f"{rumors_spread} rumor(es) circularam pela cidade")
            dynamics = run_social_dynamics(session, until_dt)
            city_life = run_city_life(session, until_dt)
            if dynamics["graph_changes"]:
                social.append(f"{dynamics['graph_changes']} mudança(s) no grafo social")
            if dynamics["events_resolved"]:
                social.append(f"{dynamics['events_resolved']} atividade(s) autônoma(s) terminaram")
            if dynamics["rumors"]:
                social.append(f"{dynamics['rumors']} pessoa(s) ouviram rumores")
            if dynamics["reputation_updates"]:
                social.append(f"{dynamics['reputation_updates']} perfil(is) ganharam visibilidade")
            city_counts = sum(value for key, value in city_life.items() if key not in {"highlights"} and isinstance(value, int))
            if city_counts:
                social.append(f"{city_counts} pequenas mudanças aconteceram na vida cotidiana")
            social.extend((arc_highlights + intent_highlights + goal_highlights + rumor_highlights + dynamics["highlights"] + city_life["highlights"])[:18])

            # A atividade do jogador também entra no ecossistema: NPCs que o seguem
            # podem reagir, mas isso não é a única fonte de vida do feed.
            likes, comments = npc_social_reactions(session)
            if likes or comments:
                social.append(f"{comments} respostas e {likes} reações aos seus posts")
        except Exception:  # noqa: BLE001
            logger.exception("autonomous social simulation failed")
            social.append("a atividade social ficou parcialmente indisponível nesta rodada")

    state.last_catchup_at = utcnow()
    paid = sum(p["amount"] for p in economy["payments"])
    summary_parts = []
    if economy["payments"]:
        summary_parts.append(f"{len(economy['payments'])} turnos de trabalho pagos (R$ {paid:.0f} no total)")
    if economy["locations"]:
        summary_parts.append(f"{economy['locations']} moradores seguiram para seus lugares")
    if stale_sessions:
        summary_parts.append(f"{stale_sessions} sessão(ões) de evento antiga(s) arquivada(s) pelo tempo")
    if idle_sessions:
        summary_parts.append(f"{idle_sessions} conversa(s) ficaram ociosas")
    if future_social:
        summary_parts.append(f"{len(future_social)} novidade(s) social(is) chegaram enquanto você estava fora")
    if social:
        summary_parts.append(", ".join(social))
    summary = "; ".join(summary_parts) or "O tempo passou sem grandes novidades."
    session.add(
        SimulationLog(
            kind="auto" if minutes is None else "catchup",
            elapsed_minutes=elapsed,
            summary=summary[:2000],
            payload={
                "payments": economy["payments"][:20],
                "social": social + future_social,
                "elapsed_minutes": elapsed,
            },
        )
    )
    session.add(state)
    session.commit()
    session.refresh(state)
    return {
        "elapsed_minutes": elapsed,
        "from": from_dt.isoformat(),
        "to": until_dt.isoformat(),
        "payments": economy["payments"],
        "locations": economy["locations"],
        "social": social,
        "summary": summary,
    }


def latest_report(session: Session, limit: int = 10) -> list[SimulationLog]:
    return session.exec(
        select(SimulationLog)
        .where(SimulationLog.kind.in_(["auto", "catchup"]))
        .order_by(SimulationLog.id.desc())
        .limit(limit)
    ).all()