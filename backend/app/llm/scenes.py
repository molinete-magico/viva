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


def _fallback_scene(*, event_title: str, event_description: str, participants: list[str], player_name: str, turn_index: int, last_action: str | None = None, free_text_action: str | None = None) -> dict[str, Any]:
    people = [p for p in participants if p and p != player_name]
    subject = people[0] if people else None
    detail = event_description.strip() or event_title
    if turn_index == 0:
        narrative = f"{detail}. {subject} está com você na situação." if subject else f"{detail}. A situação começa sem outro participante identificado."
    else:
        if subject:
            narrative = f"{subject} reage ao que aconteceu e mantém a conversa em andamento."
        else:
            narrative = "A situação continua a partir do que aconteceu na rodada anterior."
    dialogue = [{"speaker": subject, "line": "Oi." if turn_index == 0 else "Uhum."}] if subject else []
    return {
        "narrative": narrative[:8000],
        "dialogue": dialogue,
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
    event_description: str,
    host_name: str,
    participants: list[str],
    participant_context: str,
    player_name: str,
    chronology: str,
    narrative_so_far: list[str],
    last_action: str | None,
    free_text_action: str | None = None,
) -> tuple[str, str]:
    who = ", ".join(p for p in participants if p and p != player_name) or "nenhum outro participante"
    history = "\n".join(narrative_so_far[-8:]) or "A cena acabou de começar."
    action_text = last_action or "(ainda não agiu)"
    free_text_text = free_text_action or "(nenhuma ação livre)"
    system_prompt = (
        "Você conduz uma cena interativa que acontece de verdade em Vila Serena. "
        "Não escreva como livro, filme, narrador épico ou RPG genérico. "
        "A cena deve parecer uma situação cotidiana com pessoas específicas.\n\n"
        f"Evento: {event_title}. Anfitrião: {host_name}.\n"
        f"Descrição: {event_description or event_title}.\n"
        f"Participantes: {who}.\n"
        f"Contexto de cada participante:\n{participant_context}\n\n"
        "FORMATO — responda APENAS com JSON válido, sem markdown, com estas 4 chaves:\n"
        '{"narrative": "...", "dialogue": [{"speaker": "...", "line": "..."}], '
        '"actions": [{"id": "...", "label": "...", "effects": {"memory": "...", "memory_importance": 20}, "hint": "..."}], '
        '"flags": {"complete": false}}\n\n'
        "NATURALIDADE:\n"
        "- A narrativa descreve somente o que está acontecendo na cena. Não narre pensamentos, sentimentos ou "
        "decisões do jogador como se fossem fatos; deixe isso para o jogador.\n"
        "- Evite frases genéricas quando não houver um detalhe concreto.\n"
        "- Não faça todos os personagens reagirem ao jogador ao mesmo tempo. Alguns podem estar ocupados, "
        "distraídos, discordar ou nem responder.\n"
        "- Cada fala deve ter uma razão para existir. Pessoas não precisam dizer exatamente o que sentem.\n"
        "- Não faça diálogos excessivamente articulados. Frases incompletas, interrupções e respostas curtas "
        "são aceitáveis quando combinarem com a pessoa.\n"
        "- Não transforme uma situação banal em um grande momento. Pequenos acontecimentos também podem ser o resultado.\n"
        "- Não termine cada rodada com suspense, lição, revelação ou mudança de relacionamento.\n"
        "- Não trate todas as ações do jogador como boas decisões. Pessoas podem reagir mal, ignorar, discordar "
        "ou simplesmente seguir a própria rotina.\n\n"
        f"CONTINUIDADE: a última ação foi: {action_text}. A ação livre, se houver, é: {free_text_text}. "
        "Use as cenas anteriores para manter continuidade, mas não repita informações apenas para mostrar que lembra.\n\n"
        "AÇÕES: gere 3 a 5 opções concretas e diferentes entre si. Elas são sugestões, não limites. "
        "Uma ação pode ser banal, social, inconveniente, impulsiva ou encerrar a participação. "
        "Não use sempre observar/conversar/ajudar/ir embora com palavras diferentes. "
        "Os effects representam consequências possíveis e devem ser específicos ao que aconteceu.\n\n"
        "ENCERRAMENTO: flags.complete=true somente se a situação realmente terminou ou perdeu seu motivo "
        "para continuar. Não encerre a cena só porque houve uma boa fala ou uma pequena decisão.\n"
        "Escreva narrative em 2 a 4 frases curtas e dialogue com 1 a 3 falas. Não faça monólogos."
    )
    user_prompt = (
        f"Contexto: {chronology}.\n"
        f"Você é {player_name}. O anfitrião é {host_name}.\n"
        f"Cenas anteriores:\n{history}\n\n"
        f"Ação livre do jogador nesta rodada: {free_text_text}\n"
        "Continue a situação a partir do que realmente aconteceu. Se houver ação livre, ela tem prioridade "
        "sobre as opções sugeridas."
    )
    return system_prompt, user_prompt


async def generate_scene(
    provider,
    *,
    event_title: str,
    event_description: str,
    host_name: str,
    participants: list[str],
    participant_context: str,
    player_name: str,
    chronology: str,
    narrative_so_far: list[str],
    last_action: str | None = None,
    free_text_action: str | None = None,
    turn_index: int = 0,
) -> dict[str, Any]:
    system_prompt, user_prompt = build_scene_prompt(
        event_title=event_title,
        event_description=event_description,
        host_name=host_name,
        participants=participants,
        participant_context=participant_context,
        player_name=player_name,
        chronology=chronology,
        narrative_so_far=narrative_so_far,
        last_action=last_action,
        free_text_action=free_text_action,
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
            event_description=event_description,
            participants=participants,
            player_name=player_name,
            turn_index=turn_index,
            last_action=last_action,
            free_text_action=free_text_action,
        )
    data = _extract_json(text)
    if data is None:
        return _fallback_scene(
            event_title=event_title,
            event_description=event_description,
            participants=participants,
            player_name=player_name,
            turn_index=turn_index,
            last_action=last_action,
            free_text_action=free_text_action,
        )
    narrative = data.get("narrative", "").strip()[:8000]
    dialogue = data.get("dialogue") if isinstance(data.get("dialogue"), list) else []
    actions = data.get("actions") if isinstance(data.get("actions"), list) else []
    actions = [a for a in actions if isinstance(a, dict) and a.get("id") and a.get("label")][:5]
    if not narrative or not actions:
        return _fallback_scene(
            event_title=event_title,
            event_description=event_description,
            participants=participants,
            player_name=player_name,
            turn_index=turn_index,
            last_action=last_action,
            free_text_action=free_text_action,
        )
    return {
        "narrative": narrative,
        "dialogue": dialogue[:3],
        "actions": actions,
        "_flags": data.get("flags") if isinstance(data.get("flags"), dict) else None,
    }


OUTCOME_SYSTEM = (
    "Você resume uma experiência que aconteceu de verdade em Vila Serena. "
    "Escreva como uma pessoa contando depois o que aconteceu, sem narrador épico, "
    "sem lição de vida e sem linguagem de sistema. Português do Brasil. "
    "Se houve algo específico ou estranho, prefira esse detalhe a uma conclusão genérica. "
    "Não invente sentimentos ou consequências que não aparecem no histórico."
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
        f"Evento: {event_title}. Personagem: {player_name}. Pessoas presentes: {who}.\n\n"
        f"O que aconteceu:\n{history}\n\n"
        "Resuma em 1 a 3 frases o que aconteceu de fato. Dê preferência a nomes, ações e detalhes "
        "concretos. Não use 'foi uma experiência', 'ficou uma lembrança', 'saiu mais próximo' ou "
        "outras conclusões genéricas se o histórico não sustentar isso."
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
