"""Microdinâmica da cidade.

Esta camada adiciona vida cotidiana sem introduzir novas tabelas:
- presença e densidade social por local;
- afinidades e encontros fortuitos;
- solidão e busca por companhia;
- rotina de hobbies;
- manutenção de amizades e rivalidades;
- check-ins e conversas ambientais;
- oportunidades sociais;
- descoberta de lugares;
- microeventos locais;
- consequências de reputação;
- notificações relevantes;
- memória contextual.

As decisões são determinísticas para que catch-up repetido seja idempotente.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models import (
    Character,
    Event,
    EventParticipant,
    Follow,
    Location,
    Memory,
    Notification,
    Post,
    Relationship,
)
from app.services import relationship_service as rel


def score(seed: str) -> float:
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF


def key(prefix: str, *parts: object) -> str:
    return "-".join([prefix, *(str(p) for p in parts)])


def already(session: Session, character_id: int, marker: str) -> bool:
    return session.exec(
        select(Memory).where(
            Memory.owner_character_id == character_id,
            Memory.dedupe_key == marker,
        )
    ).first() is not None


def remember(session: Session, owner: Character, other: Character | None, text: str,
             kind: str, marker: str, moment: datetime, importance: int = 25) -> bool:
    if owner.id is None or already(session, owner.id, marker):
        return False
    rel.add_memory(
        session,
        owner_character_id=owner.id,
        other_character_id=other.id if other else None,
        content=text[:4000],
        kind=kind,
        importance=importance,
        context={"world_time": moment.isoformat()},
        dedupe_key=marker,
        occurred_at=moment,
    )
    return True


def normalized(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _people_at(session: Session, location_id: int) -> list[Character]:
    return session.exec(
        select(Character).where(Character.current_location_id == location_id)
    ).all()


def _relationship(session: Session, a: Character, b: Character) -> Relationship | None:
    if a.id is None or b.id is None:
        return None
    return rel.relationship_between(session, a.id, b.id)


def _compatibility(a: Character, b: Character, relationship: Relationship | None) -> float:
    own = {str(x).lower() for x in (a.hobbies or []) + (a.likes or [])}
    theirs = {str(x).lower() for x in (b.hobbies or []) + (b.likes or [])}
    score_value = min(4.0, len(own & theirs) * 1.25)
    dislikes = {str(x).lower() for x in (a.dislikes or [])}
    score_value -= min(3.0, len(dislikes & theirs) * 1.4)
    if relationship:
        score_value += relationship.friendship * 0.035
        score_value += relationship.trust * 0.02
        score_value += relationship.respect * 0.015
        score_value -= relationship.tension * 0.045
    return score_value


def _social_personality(character: Character) -> tuple[float, float]:
    personality = character.personality or {}
    sociability = float(personality.get("sociability", personality.get("social", 0.5)) or 0.5)
    energy = float(personality.get("energy", 0.5) or 0.5)
    return max(0.0, min(1.0, sociability)), max(0.0, min(1.0, energy))


def social_density(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Locais cheios viram pontos de encontro e geram memória contextual."""
    locations = session.exec(select(Location).where(Location.is_public.is_(True))).all()
    changes = 0
    highlights: list[str] = []
    for location in locations:
        people = [p for p in _people_at(session, location.id) if p.is_npc]
        if len(people) < 2:
            continue
        marker = key("density", location.id, moment.date())
        for person in people:
            if person.id is None or already(session, person.id, marker):
                continue
            if score(f"density:{location.id}:{person.id}:{moment.date()}") < min(0.9, 0.25 + len(people) * 0.08):
                remember(
                    session, person, None,
                    f"Passei por {location.name} quando havia bastante gente por perto.",
                    "location_density", marker, moment, 16,
                )
                changes += 1
        if len(people) >= 4 and score(f"buzz:{location.id}:{moment.date()}") < 0.45:
            marker_post = key("location-buzz", location.id, moment.date())
            if session.exec(select(Post).where(
                Post.kind == "location",
                Post.location_id == location.id,
                Post.created_at >= moment.replace(hour=0, minute=0, second=0, microsecond=0),
                Post.created_at <= moment,
            )).first() is None:
                author = max(people, key=lambda p: _social_personality(p)[0])
                session.add(Post(
                    author_character_id=author.id,
                    content=f"{location.name} está movimentado hoje. Parece que todo mundo resolveu aparecer.",
                    kind="location",
                    location_id=location.id,
                    created_at=moment,
                ))
                session.commit()
                highlights.append(f"{location.name} ficou movimentado")
    return changes, highlights[:8]


def serendipitous_encounters(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Duas pessoas compatíveis no mesmo lugar podem transformar coincidência em relação."""
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    changes = 0
    highlights: list[str] = []
    for index, left in enumerate(npcs):
        if left.id is None or left.current_location_id is None:
            continue
        for right in npcs[index + 1:]:
            if right.id is None or right.current_location_id != left.current_location_id:
                continue
            relationship = _relationship(session, left, right)
            fit = _compatibility(left, right, relationship)
            marker = key("serendipity", left.id, right.id, moment.date())
            if already(session, left.id, marker):
                continue
            probability = 0.12 + max(0.0, min(0.55, fit * 0.08))
            probability += (_social_personality(left)[0] + _social_personality(right)[0]) * 0.08
            if score(f"encounter:{marker}") >= probability:
                continue
            rel.apply_changes(session, left.id, right.id, {
                "familiarity": 1,
                "respect": 1 if fit > 1 else 0,
                "friendship": 1 if fit > 2 else 0,
            }, log=False)
            remember(session, left, right, f"Encontrei {right.name} por acaso em um lugar da cidade.", "serendipitous_encounter", marker, moment, 32)
            remember(session, right, left, f"Encontrei {left.name} por acaso em um lugar da cidade.", "serendipitous_encounter", marker + "-r", moment, 32)
            changes += 1
            highlights.append(f"{left.name} encontrou {right.name} por acaso")
    return changes, highlights[:8]


def loneliness_and_companionship(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """NPCs muito isolados procuram companhia; os muito tensionados procuram distância."""
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    actions = 0
    highlights: list[str] = []
    for npc in npcs:
        if npc.id is None:
            continue
        relationships = rel.list_for_character(session, npc.id)
        if not relationships:
            continue
        best = max(relationships, key=lambda r: r.friendship + r.trust + r.familiarity - r.tension)
        target_id = rel.pair_other_id(best, npc.id)
        target = session.get(Character, target_id)
        if target is None or target.id is None:
            continue
        sociability, energy = _social_personality(npc)
        marker = key("companionship", npc.id, moment.date())
        if already(session, npc.id, marker):
            continue
        quality = best.friendship + best.trust + best.familiarity - best.tension
        if quality < 20 and sociability > 0.55 and score(f"seek:{npc.id}:{moment.date()}") < 0.35:
            rel.apply_changes(session, npc.id, target.id, {"familiarity": 1, "friendship": 1}, log=False)
            remember(session, npc, target, f"Senti falta de companhia e pensei em {target.name}.", "companionship_need", marker, moment, 28)
            actions += 1
            highlights.append(f"{npc.name} procurou companhia")
        elif best.tension >= 50 and energy > 0.4:
            remember(session, npc, target, f"Preferi dar um pouco de espaço para {target.name}.", "social_distance", marker, moment, 25)
            actions += 1
            highlights.append(f"{npc.name} deu espaço a {target.name}")
    return actions, highlights[:8]


def hobby_routines(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Hobbies influenciam o local onde o NPC aparece e quem ele encontra."""
    locations = session.exec(select(Location)).all()
    by_id = {location.id: location for location in locations}
    actions = 0
    highlights: list[str] = []
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    for npc in npcs:
        if npc.id is None or not npc.hobbies:
            continue
        favorite_ids = [int(x) for x in (npc.favorite_location_ids or []) if str(x).isdigit()]
        target_location = by_id.get(favorite_ids[0]) if favorite_ids else None
        if target_location is None:
            continue
        marker = key("hobby-routine", npc.id, moment.date(), moment.hour // 4)
        if already(session, npc.id, marker):
            continue
        if score(f"hobby:{npc.id}:{moment.date()}:{moment.hour // 4}") < 0.35:
            npc.current_location_id = target_location.id
            session.add(npc)
            remember(session, npc, None, f"Passei algum tempo em {target_location.name} para cuidar de um hobby.", "hobby_routine", marker, moment, 22)
            actions += 1
            highlights.append(f"{npc.name} foi praticar um hobby em {target_location.name}")
    if actions:
        session.commit()
    return actions, highlights[:8]


def repair_friendships(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Relações boas recebem pequenos gestos de manutenção; amizade não congela."""
    relationships = session.exec(select(Relationship)).all()
    actions = 0
    highlights: list[str] = []
    for relationship in relationships:
        if relationship.friendship < 35 or relationship.tension >= 30:
            continue
        if relationship.character_a_id is None or relationship.character_b_id is None:
            continue
        a = session.get(Character, relationship.character_a_id)
        b = session.get(Character, relationship.character_b_id)
        if a is None or b is None:
            continue
        marker = key("friend-maintenance", relationship.id, moment.date())
        if already(session, a.id, marker):
            continue
        if score(f"maintain:{relationship.id}:{moment.date()}") < 0.28:
            rel.apply_changes(session, a.id, b.id, {"familiarity": 1, "trust": 1}, log=False)
            remember(session, a, b, f"Fiz questão de manter contato com {b.name}.", "friendship_maintenance", marker, moment, 30)
            remember(session, b, a, f"{a.name} fez questão de manter contato comigo.", "friendship_maintenance", marker + "-r", moment, 30)
            actions += 1
            highlights.append(f"{a.name} manteve contato com {b.name}")
    return actions, highlights[:8]


def rivalry_avoidance(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Rivais não precisam se encontrar o tempo todo; tensão altera comportamento espacial."""
    relationships = session.exec(select(Relationship).where(Relationship.tension >= 45)).all()
    actions = 0
    highlights: list[str] = []
    for relationship in relationships:
        a = session.get(Character, relationship.character_a_id)
        b = session.get(Character, relationship.character_b_id)
        if a is None or b is None or a.current_location_id != b.current_location_id:
            continue
        marker = key("rival-avoidance", relationship.id, moment.date(), moment.hour)
        if already(session, a.id, marker):
            continue
        if score(f"avoid:{relationship.id}:{moment.date()}:{moment.hour}") < 0.5:
            b_location = b.current_location_id
            alternatives = [int(x) for x in (a.favorite_location_ids or []) if str(x).isdigit() and int(x) != b_location]
            if alternatives:
                a.current_location_id = alternatives[0]
                session.add(a)
                remember(session, a, b, f"Evitei ficar no mesmo lugar que {b.name} hoje.", "rivalry_avoidance", marker, moment, 31)
                actions += 1
                highlights.append(f"{a.name} evitou {b.name}")
    if actions:
        session.commit()
    return actions, highlights[:8]


def social_opportunities(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Cria convites leves quando um grupo compatível está reunido, sem exigir ação do jogador."""
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    actions = 0
    highlights: list[str] = []
    by_location: dict[int, list[Character]] = {}
    for npc in npcs:
        if npc.current_location_id is not None:
            by_location.setdefault(npc.current_location_id, []).append(npc)
    for location_id, people in by_location.items():
        if len(people) < 3:
            continue
        host = max(people, key=lambda p: _social_personality(p)[0])
        if host.id is None:
            continue
        marker = key("social-opportunity", location_id, moment.date())
        if already(session, host.id, marker):
            continue
        if score(f"opportunity:{location_id}:{moment.date()}") > 0.35:
            continue
        location = session.get(Location, location_id)
        if location is None:
            continue
        event = Event(
            title=f"Encontro espontâneo em {location.name}",
            description="Um pequeno grupo resolveu continuar junto depois de se encontrar.",
            kind="ambient",
            status="OPEN",
            scheduled_at=moment + timedelta(minutes=30),
            location_id=location.id,
            host_character_id=host.id,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        selected = people[:5]
        for person in selected:
            if person.id == host.id:
                continue
            session.add(EventParticipant(
                event_id=event.id,
                character_id=person.id,
                status="INVITED",
                invited_at=moment,
            ))
        session.commit()
        remember(session, host, None, f"Convidei algumas pessoas para um encontro espontâneo em {location.name}.", "social_opportunity", marker, moment, 35)
        actions += 1
        highlights.append(f"Um grupo marcou um encontro em {location.name}")
    return actions, highlights[:6]


def local_discovery(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Moradores descobrem lugares novos e isso passa a influenciar sua memória."""
    locations = session.exec(select(Location)).all()
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    actions = 0
    highlights: list[str] = []
    for npc in npcs:
        if npc.id is None:
            continue
        marker = key("discovery", npc.id, moment.date())
        if already(session, npc.id, marker):
            continue
        unseen = [loc for loc in locations if loc.id not in set(int(x) for x in (npc.favorite_location_ids or []) if str(x).isdigit())]
        if not unseen or score(f"discover:{npc.id}:{moment.date()}") > 0.12:
            continue
        location = unseen[0]
        remember(session, npc, None, f"Descobri {location.name} e agora sei onde fica.", "location_discovery", marker, moment, 27)
        if score(f"favorite:{npc.id}:{location.id}") < 0.35:
            npc.favorite_location_ids = list(npc.favorite_location_ids or []) + [location.id]
            session.add(npc)
        actions += 1
        highlights.append(f"{npc.name} descobriu {location.name}")
    if actions:
        session.commit()
    return actions, highlights[:8]


def local_conversations(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Pequenas conversas ambientais deixam rastros sociais mesmo sem post ou evento."""
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    actions = 0
    highlights: list[str] = []
    for location in session.exec(select(Location)).all():
        people = [p for p in npcs if p.current_location_id == location.id]
        if len(people) < 2:
            continue
        people.sort(key=lambda p: _social_personality(p)[0], reverse=True)
        a, b = people[0], people[1]
        if a.id is None or b.id is None:
            continue
        relationship = _relationship(session, a, b)
        marker = key("ambient-chat", min(a.id, b.id), max(a.id, b.id), moment.date(), moment.hour // 3)
        if already(session, a.id, marker):
            continue
        fit = _compatibility(a, b, relationship)
        if score(f"chat:{marker}") > min(0.8, 0.28 + max(0, fit) * 0.07):
            continue
        rel.apply_changes(session, a.id, b.id, {"familiarity": 1}, log=False)
        if fit > 1:
            rel.apply_changes(session, a.id, b.id, {"friendship": 1}, log=False)
        remember(session, a, b, f"Conversei com {b.name} em {location.name}.", "ambient_conversation", marker, moment, 24)
        remember(session, b, a, f"Conversei com {a.name} em {location.name}.", "ambient_conversation", marker + "-r", moment, 24)
        actions += 1
        highlights.append(f"{a.name} conversou com {b.name} em {location.name}")
    return actions, highlights[:8]


def reputation_reactions(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Reputação alta facilita descoberta; reputação baixa não é apagada, mas gera cautela."""
    characters = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    actions = 0
    highlights: list[str] = []
    for npc in characters:
        if npc.id is None:
            continue
        followers = session.exec(select(Follow).where(Follow.followed_character_id == npc.id)).all()
        marker = key("reputation", npc.id, moment.date())
        if already(session, npc.id, marker):
            continue
        if npc.discovered_level >= 7 and score(f"reputation:{npc.id}:{moment.date()}") < 0.25:
            remember(session, npc, None, "Percebi que estou ficando conhecido na cidade.", "reputation", marker, moment, 32)
            actions += 1
            highlights.append(f"{npc.name} percebeu que está ficando conhecido")
        elif len(followers) == 0 and score(f"unknown:{npc.id}:{moment.date()}") < 0.18:
            remember(session, npc, None, "Tenho a sensação de que quase ninguém sabe quem eu sou por aqui.", "reputation", marker, moment, 22)
            actions += 1
            highlights.append(f"{npc.name} continua pouco conhecido")
    return actions, highlights[:6]


def player_relevance_notifications(session: Session, moment: datetime) -> int:
    """Só eventos socialmente relevantes chegam ao jogador; reduz ruído de notificações."""
    player_ids = {
        c.id for c in session.exec(select(Character).where(Character.user_id.is_not(None))).all()
        if c.id is not None
    }
    if not player_ids:
        return 0
    cutoff = moment - timedelta(hours=6)
    memories = session.exec(
        select(Memory).where(
            Memory.occurred_at >= cutoff,
            Memory.importance >= 55,
        ).order_by(Memory.occurred_at.desc()).limit(20)
    ).all()
    created = 0
    for memory in memories:
        if memory.other_character_id not in player_ids and memory.owner_character_id not in player_ids:
            continue
        target_id = memory.other_character_id if memory.other_character_id in player_ids else memory.owner_character_id
        if target_id is None:
            continue
        marker = key("relevance-notification", target_id, memory.id)
        if already(session, target_id, marker):
            continue
        session.add(Notification(
            character_id=target_id,
            type="CITY_RELEVANCE",
            payload={"memory_id": memory.id, "kind": memory.kind, "content": memory.content},
            created_at=moment,
        ))
        remember(
            session,
            session.get(Character, target_id),
            None,
            f"Recebi uma novidade importante da cidade: {memory.content}",
            "notification_marker",
            marker,
            moment,
            10,
        )
        created += 1
    if created:
        session.commit()
    return created


def _run_city_life_base(session: Session, moment: datetime) -> dict:
    results = {}
    results["density"], density_h = social_density(session, moment)
    results["encounters"], encounter_h = serendipitous_encounters(session, moment)
    results["companionship"], companionship_h = loneliness_and_companionship(session, moment)
    results["hobbies"], hobby_h = hobby_routines(session, moment)
    results["friendship"], friendship_h = repair_friendships(session, moment)
    results["avoidance"], avoidance_h = rivalry_avoidance(session, moment)
    results["opportunities"], opportunity_h = social_opportunities(session, moment)
    results["discoveries"], discovery_h = local_discovery(session, moment)
    results["conversations"], conversation_h = local_conversations(session, moment)
    results["reputation"], reputation_h = reputation_reactions(session, moment)
    results["notifications"] = player_relevance_notifications(session, moment)
    results["highlights"] = (
        density_h + encounter_h + companionship_h + hobby_h + friendship_h +
        avoidance_h + opportunity_h + discovery_h + conversation_h + reputation_h
    )[:18]
    return results

def reciprocity(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Gestos sociais recentes podem receber uma resposta posterior."""
    actions, highlights = 0, []
    for npc in session.exec(select(Character).where(Character.is_npc.is_(True))).all():
        if npc.id is None: continue
        memories = session.exec(select(Memory).where(Memory.owner_character_id == npc.id, Memory.kind == "social_engagement", Memory.occurred_at >= moment - timedelta(days=2)).limit(4)).all()
        for memory in memories:
            if memory.other_character_id is None: continue
            other = session.get(Character, memory.other_character_id)
            marker = key("reciprocity", memory.id, npc.id)
            if other is None or other.id is None or already(session, npc.id, marker) or score(f"reciprocity:{memory.id}:{npc.id}") >= 0.18: continue
            rel.apply_changes(session, npc.id, other.id, {"trust": 1, "respect": 1}, log=False)
            remember(session, npc, other, f"Quis retribuir uma atitude recente de {other.name}.", "reciprocity", marker, moment, 27)
            actions += 1; highlights.append(f"{npc.name} retribuiu um gesto de {other.name}"); break
    return actions, highlights[:6]

def dormant_ties(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Laços bons sem contato podem voltar à superfície."""
    actions, highlights = 0, []
    for relationship in session.exec(select(Relationship)).all():
        if relationship.friendship < 40 or relationship.tension >= 25 or not relationship.last_interaction_at: continue
        if moment - normalized(relationship.last_interaction_at) < timedelta(days=3): continue
        a = session.get(Character, relationship.character_a_id); b = session.get(Character, relationship.character_b_id)
        marker = key("dormant-tie", relationship.id, moment.date())
        if a is None or b is None or a.id is None or b.id is None or already(session, a.id, marker) or score(f"dormant:{relationship.id}:{moment.date()}") >= 0.24: continue
        rel.apply_changes(session, a.id, b.id, {"familiarity": 1}, log=False)
        remember(session, a, b, f"Depois de alguns dias, voltei a pensar em {b.name}.", "dormant_tie", marker, moment, 28)
        actions += 1; highlights.append(f"{a.name} retomou um laço antigo com {b.name}")
    return actions, highlights[:6]

def tension_spillover(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Conflitos fortes são percebidos por pessoas próximas sem criar inimigos artificiais."""
    actions, highlights = 0, []
    for conflict in session.exec(select(Relationship).where(Relationship.tension >= 60)).all():
        a = session.get(Character, conflict.character_a_id); b = session.get(Character, conflict.character_b_id)
        if a is None or b is None or a.id is None or b.id is None: continue
        for row in session.exec(select(Follow).where(Follow.follower_character_id == a.id)).all()[:4]:
            observer = session.get(Character, row.followed_character_id); marker = key("spillover", conflict.id, row.followed_character_id, moment.date())
            if observer is None or observer.id in (a.id, b.id) or already(session, observer.id, marker): continue
            if score(f"spillover:{conflict.id}:{observer.id}:{moment.date()}") < 0.18:
                remember(session, observer, a, f"Percebi que {a.name} está em conflito com {b.name}.", "tension_spillover", marker, moment, 24)
                actions += 1; highlights.append(f"{observer.name} percebeu uma tensão social")
    return actions, highlights[:6]

def location_loyalty(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Frequência cria apego a lugares e reforça rotinas futuras."""
    actions = 0
    for npc in session.exec(select(Character).where(Character.is_npc.is_(True))).all():
        if npc.id is None or npc.current_location_id is None: continue
        marker = key("location-loyalty", npc.id, npc.current_location_id, moment.date())
        if already(session, npc.id, marker) or score(f"loyalty:{npc.id}:{npc.current_location_id}:{moment.date()}") > 0.25: continue
        favorite = list(npc.favorite_location_ids or [])
        if npc.current_location_id not in favorite:
            npc.favorite_location_ids = favorite + [npc.current_location_id]; session.add(npc); actions += 1
    if actions: session.commit()
    return actions, []

def _run_city_life_previous(session: Session, moment: datetime) -> dict:
    result = _run_city_life_base(session, moment)
    extra = [reciprocity(session, moment), dormant_ties(session, moment), tension_spillover(session, moment), location_loyalty(session, moment)]
    result["second_order"] = sum(item[0] for item in extra)
    result["highlights"] = (result["highlights"] + [h for _, hs in extra for h in hs])[:28]
    return result

def reputation_discovery(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Visibilidade alta cria descoberta orgânica sem forçar follow."""
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    actions, highlights = 0, []
    for popular in npcs:
        if popular.id is None or popular.discovered_level < 6:
            continue
        followers = session.exec(select(Follow).where(Follow.followed_character_id == popular.id)).all()
        candidates = [n for n in npcs if n.id != popular.id and not any(f.follower_character_id == n.id for f in followers)]
        for viewer in candidates[:4]:
            marker = key("reputation-discovery", popular.id, viewer.id, moment.date())
            if already(session, viewer.id, marker) or score(f"discover-popular:{popular.id}:{viewer.id}:{moment.date()}") > 0.08:
                continue
            rel.apply_changes(session, viewer.id, popular.id, {"familiarity": 1}, log=False)
            remember(session, viewer, popular, f"Comecei a prestar atenção em {popular.name}, que parece estar ficando conhecido.", "reputation_discovery", marker, moment, 23)
            actions += 1
            highlights.append(f"{viewer.name} descobriu {popular.name}")
            break
    return actions, highlights[:6]


def event_social_echo(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Eventos concluídos podem virar conversa pública no feed."""
    events = session.exec(select(Event).where(Event.status == "COMPLETED", Event.scheduled_at >= moment - timedelta(hours=6), Event.scheduled_at <= moment).limit(8)).all()
    actions, highlights = 0, []
    for event in events:
        host = session.get(Character, event.host_character_id) if event.host_character_id else None
        if host is None or host.id is None:
            continue
        marker = key("event-echo", event.id)
        if already(session, host.id, marker):
            continue
        session.add(Post(
            author_character_id=host.id,
            content=f"Foi bom encontrar gente em {event.title}.",
            kind="event",
            location_id=event.location_id,
            event_id=event.id,
            created_at=moment,
        ))
        session.commit()
        remember(session, host, None, f"Compartilhei um pequeno eco de {event.title} no feed.", "event_social_echo", marker, moment, 22)
        actions += 1
        highlights.append(f"{host.name} comentou sobre {event.title}")
    return actions, highlights[:6]


def fresh_social_connections(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Moradores sem vínculo podem iniciar uma relação quando a convivência se repete."""
    npcs = session.exec(select(Character).where(Character.is_npc.is_(True))).all()
    actions, highlights = 0, []
    for left in npcs:
        if left.id is None or left.current_location_id is None:
            continue
        candidates = [x for x in npcs if x.id != left.id and x.current_location_id == left.current_location_id]
        candidates.sort(key=lambda x: _compatibility(left, x, _relationship(session, left, x)), reverse=True)
        for right in candidates[:2]:
            if right.id is None or _relationship(session, left, right) is not None:
                continue
            marker = key("fresh-connection", left.id, right.id, moment.date())
            if already(session, left.id, marker) or score(f"fresh:{left.id}:{right.id}:{moment.date()}") > 0.22:
                continue
            rel.apply_changes(session, left.id, right.id, {"familiarity": 1}, log=False)
            remember(session, left, right, f"Comecei a conhecer {right.name} depois de encontrá-lo várias vezes.", "fresh_connection", marker, moment, 30)
            remember(session, right, left, f"Comecei a conhecer {left.name} depois de encontrá-lo várias vezes.", "fresh_connection", marker+"-r", moment, 30)
            actions += 1
            highlights.append(f"{left.name} começou a conhecer {right.name}")
            break
    return actions, highlights[:6]


def location_activity_affinity(session: Session, moment: datetime) -> tuple[int, list[str]]:
    """Atividades de um local reforçam afinidades quando combinam com hobbies do NPC."""
    actions, highlights = 0, []
    for npc in session.exec(select(Character).where(Character.is_npc.is_(True))).all():
        if npc.id is None or npc.current_location_id is None:
            continue
        location = session.get(Location, npc.current_location_id)
        if location is None or not location.activities:
            continue
        interests = {str(x).lower() for x in (npc.hobbies or []) + (npc.likes or [])}
        matching = [str(x) for x in location.activities if str(x).lower() in interests]
        if not matching:
            continue
        marker = key("activity-affinity", npc.id, location.id, moment.date())
        if already(session, npc.id, marker):
            continue
        remember(session, npc, None, f"Em {location.name}, encontrei uma atividade que combina comigo: {matching[0]}.", "activity_affinity", marker, moment, 24)
        actions += 1
    return actions, highlights[:4]


def run_city_life(session: Session, moment: datetime) -> dict:
    result = _run_city_life_base(session, moment)
    extra = [
        reciprocity(session, moment),
        dormant_ties(session, moment),
        tension_spillover(session, moment),
        location_loyalty(session, moment),
        reputation_discovery(session, moment),
        event_social_echo(session, moment),
        fresh_social_connections(session, moment),
        location_activity_affinity(session, moment),
    ]
    result["second_order"] = sum(item[0] for item in extra)
    result["highlights"] = (result["highlights"] + [h for _, hs in extra for h in hs])[:32]
    return result
