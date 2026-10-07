from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm.base import LLMError
from app.llm.prompts import complete_with_timeout

logger = logging.getLogger("viva.scenes")

MODEL_SCENE = "quick"

FALLBACK_ACTIONS = [
    {"id": "observar", "label": "Observar o que está acontecendo", "effects": {"familiarity": 1}, "hint": "ganha familiaridade"},
    {"id": "conversar", "label": "Conversar com quem está perto", "effects": {"friendship": 1}, "hint": "aproxima alguém"},
    {"id": "ajudar", "label": "Oferecer ajuda ou se envolver", "effects": {"trust": 2}, "hint": "ganha confiança"},
    {"id": "evitar", "label": "Pisar no freio e só aproveitar", "effects": {"tension": -1}, "hint": "reduz tensão"},
    {"id": "deixar", "label": "Dizer que está na hora de ir", "effects": {}, "hint": "encerra a cena"},
]


def _fallback_scene(*, event_title: str, participants: list[str], player_name: str, turn_index: int) -> dict[str, Any]:
    people = ", ".join(p for p in participants if p and p != player_name) or "os presentes"
    if turn_index == 0:
        narrative = (
            f"{event_title}. Você chega e sente o clima: gente conversando, risada baixa. "
            f"{people} estão por perto e todo mundo parece esperar você fazer o primeiro movimento."
        )
    else:
        narrative = (
            f"A cena segue em {event_title}. {people} continuam por ali; você percebe que suas "
            "escolhas estão mudando aos poucos como as pessoas tratam você."
        )
    return {
        "narrative": narrative,
        "dialogue": [
            {"speaker": people.split(", ")[0], "line": "A vida anda sempre por aqui, hein."}
        ],
        "actions": [dict(action) for action in FALLBACK_ACTIONS],
    }


def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("narrative"), str):
        return None
    return data


def build_scene_prompt(
    *,
    event_title: str,
    location_name: str,
    host_name: str,
    participants: list[str],
    player_name: str,
    chronology: str,
    narrative_so_far: list[str],
    last_action: str | None,
) -> tuple[str, str]:
    who = ", ".join(p for p in participants if p and p != player_name) or "os presentes"
    history = "\n".join(narrative_so_far[-8:]) or "A cena acabou de começar."
    action_text = last_action or "(ainda não agiu)"
    system_prompt = (
        "Você é o narrador de uma cena interativa de RPG de cidade pequena brasileira, ambientada "
        f"na Vila Serena. A cena é \"{event_title}\".\n"
        f"Saia APENAS um JSON válido, sem markdown, com exatamente 3 chaves:\n"
        '{"narrative": "...", "dialogue": [{"speaker": "...", "line": "..."}], "actions": [{"id": "...", "label": "...", "effects": {"memory": "...", "memory_importance": 20}, "hint": "..."}]}\n'
        "Regras: narrative em português do Brasil, 2 a 4 frases, avançando a cena com o impacto da "
        f"última ação do jogador ({action_text}); dialogue 1 a 3 falas dos participantes "
        f"({who}, com {host_name} entre eles) no tom deles e coerentes com as versões anteriores; "
        "actions com 3 a 5 opções, id curto em snake_case, label em PT-BR, e effects podendo conter "
        '"money" (variação em R$), uma relação ("bosst/menos" nos campos familiarity, friendship, trust, '
        'romance, respect, tension) e/ou "memory" (memória que o jogador guarda).'
    )
    user_prompt = (
        f"Contexto: {chronology} no {location_name}.\n"
        f"Você é {player_name}. O anfitrião é {host_name}.\n"
        f"Cenas anteriores:\n{history}\n\n"
        "Gere a próxima cena agora."
    )
    return system_prompt, user_prompt


async def generate_scene(
    provider,
    *,
    event_title: str,
    location_name: str,
    host_name: str,
    participants: list[str],
    player_name: str,
    chronology: str,
    narrative_so_far: list[str],
    last_action: str | None = None,
    turn_index: int = 0,
) -> dict[str, Any]:
    system_prompt, user_prompt = build_scene_prompt(
        event_title=event_title,
        location_name=location_name,
        host_name=host_name,
        participants=participants,
        player_name=player_name,
        chronology=chronology,
        narrative_so_far=narrative_so_far,
        last_action=last_action,
    )
    try:
        text = await complete_with_timeout(
            provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            personality={"tone": "narrador de histórias"},
            model=MODEL_SCENE,
        )
    except LLMError as exc:
        logger.warning("scene generation failed, using fallback: %s", exc)
        return _fallback_scene(
            event_title=event_title,
            participants=participants,
            player_name=player_name,
            turn_index=turn_index,
        )
    data = _extract_json(text)
    if data is None:
        return _fallback_scene(
            event_title=event_title,
            participants=participants,
            player_name=player_name,
            turn_index=turn_index,
        )
    narrative = data.get("narrative", "").strip()[:8000]
    dialogue = data.get("dialogue") if isinstance(data.get("dialogue"), list) else []
    actions = data.get("actions") if isinstance(data.get("actions"), list) else []
    actions = [a for a in actions if isinstance(a, dict) and a.get("id") and a.get("label")][:5]
    if not narrative or not actions:
        return _fallback_scene(
            event_title=event_title,
            participants=participants,
            player_name=player_name,
            turn_index=turn_index,
        )
    return {
        "narrative": narrative,
        "dialogue": dialogue[:3],
        "actions": actions,
        "_flags": data.get("flags") if isinstance(data.get("flags"), dict) else None,
    }

OUTCOME_SYSTEM = (
    "Você é o narrador de uma cidade pequena brasileira chamada Vila Serena. "
    "Resuma em português do Brasil, em 2 a 4 frases, o que ficou desse encontro "
    "para o personagem do jogador. Não use aspas. Não mencione o sistema."
)


def build_outcome_prompt(
    *,
    event_title: str,
    player_name: str,
    participant_names: list[str],
    narrative_so_far: list[str],
) -> tuple[str, str]:
    who = ", ".join(participant_names) or "os presentes"
    history = "\n".join(narrative_so_far[-10:]) or "A cena acabou de começar."
    user_prompt = (
        f"Evento: {event_title}. Você é {player_name}. Quem esteve por perto: {who}.\n\n"
        f"Cenas vividas:\n{history}\n\nResuma o que {player_name} leva dessa experiência."
    )
    return OUTCOME_SYSTEM, user_prompt


async def generate_outcome_summary(
    provider,
    *,
    event_title: str,
    player_name: str,
    participant_names: list[str],
    narrative_so_far: list[str],
) -> str:
    system_prompt, user_prompt = build_outcome_prompt(
        event_title=event_title,
        player_name=player_name,
        participant_names=participant_names,
        narrative_so_far=narrative_so_far,
    )
    try:
        text = await complete_with_timeout(
            provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            personality={"tone": "narrador de histórias"},
            model=MODEL_SCENE,
            timeout=15.0,
        )
        text = text.strip().strip('"')
        if text:
            return text[:2000]
    except LLMError:
        pass
    people = ", ".join(p for p in participant_names if p and p != player_name)
    if people:
        return f"Você passou um bom tempo com {people} em {event_title} e saiu de lá mais perto de cada um."
    return f"Você viveu {event_title} na Vila Serena e levou essa história na memória."
