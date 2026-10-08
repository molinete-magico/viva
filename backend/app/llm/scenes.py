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


def _fallback_scene(
    *,
    event_title: str,
    event_description: str,
    participants: list[str],
    player_name: str,
    turn_index: int,
    last_action: str | None = None,
    free_text_action: str | None = None,
    narrative_so_far: list[str] | None = None,
) -> dict[str, Any]:
    """Last-resort scene that still follows the immediate conversation."""
    people = [p for p in participants if p and p != player_name]
    subject = people[0] if people else None
    detail = event_description.strip() or event_title
    action = (free_text_action or last_action or "").strip()
    lower = action.casefold()
    history = "\n".join(narrative_so_far[-6:]) if narrative_so_far else ""

    if turn_index == 0:
        narrative = (
            f"{detail}. {subject} está com você e a atividade começa sem pressa."
            if subject
            else f"{detail}. A situação começa."
        )
        line = "E aí. Chegou na hora boa." if subject else None
    elif subject:
        if any(term in lower for term in ("como você está", "tudo de boa", "e aí", "oi", "opa")):
            narrative = f"{subject} responde ao cumprimento e mantém a atenção no que vocês vieram fazer."
            line = "Tô de boa. Só tava mexendo nisso aqui. E você?"
        elif any(term in lower for term in ("quer escutar", "o que", "qual", "vamos ouvir", "vinil", "disco", "música", "metallica", "metallica", "red hot")):
            narrative = f"{subject} olha para a coleção de discos e começa a separar algumas opções."
            line = "Bora. Tenho uns aqui que combinam. Quer escolher ou deixo eu decidir?"
        elif any(term in lower for term in ("só uhum", "fala alguma coisa", "conversa", "responde", "tá quieto", "ta quieto")):
            narrative = f"{subject} percebe que estava respondendo no automático e volta a prestar atenção na conversa."
            line = "Foi mal, tava viajando. Eu tava pensando justamente no que colocar primeiro."
        elif any(term in lower for term in ("sim", "bora", "vamos", "quero", "pode ser", "manda a boa")):
            narrative = f"{subject} entende a ideia e começa a agir sobre ela, em vez de deixar a conversa parada."
            line = "Então fechou. Deixa eu pegar aqui."
        else:
            narrative = f"{subject} leva em conta o que você acabou de dizer e responde sem mudar o assunto à força."
            line = "Pode ser. Espera, deixa eu pensar nisso direito."
    else:
        narrative = "A situação continua a partir da última coisa que aconteceu."
        line = None

    dialogue = [{"speaker": subject, "line": line}] if subject and line else []
    return {
        "narrative": narrative[:8000],
        "dialogue": dialogue,
        "actions": [
            {"id": "seguir_assunto", "label": "Continuar o assunto", "effects": {}, "hint": "seguir a conversa"},
            {"id": "observar", "label": "Prestar atenção no que está acontecendo", "effects": {}, "hint": "ver o que acontece"},
            {"id": "mudar_assunto", "label": "Puxar outro assunto", "effects": {}, "hint": "mudar o rumo da conversa"},
            {"id": "encerrar", "label": "Dizer que já vai embora", "effects": {}, "hint": "encerrar a situação"},
        ],
    }


def _dialogue_is_usable(
    dialogue: Any,
    participants: list[str],
    player_name: str,
    previous_lines: list[str] | None = None,
) -> bool:
    if not isinstance(dialogue, list):
        return False
    allowed = {p.strip().casefold() for p in participants if p and p.strip() and p != player_name}
    if allowed and not dialogue:
        return False
    previous = {line.strip().casefold() for line in (previous_lines or []) if line.strip()}
    generic = {"uhum", "hum", "hmm", "oi", "ok", "tá", "ta", "sim", "beleza", "pode ser"}
    for item in dialogue[:3]:
        if not isinstance(item, dict):
            return False
        speaker = str(item.get("speaker", "")).strip()
        line = str(item.get("line", "")).strip()
        if not speaker or not line:
            return False
        if allowed and speaker.casefold() not in allowed:
            return False
        normalized = line.casefold()
        if normalized in generic or normalized in previous:
            return False
        if len(line.split()) < 2:
            return False
    return True

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
        "Você conduz uma situação social interativa em Vila Serena. "
        "A pessoa jogadora está vivendo a situação com moradores que têm personalidade, memória, objetivos e vontade própria. "
        "O objetivo não é contar uma história pronta: é simular o que aconteceria se a pessoa realmente estivesse ali.\n\n"
        f"Situação: {event_title}. Anfitrião: {host_name}.\n"
        f"Contexto: {event_description or event_title}.\n"
        f"Pessoas realmente presentes: {who}.\n"
        f"Informações dos personagens:\n{participant_context}\n\n"
        "REGRA CENTRAL — REAÇÃO CAUSAL:\n"
        "- A ÚLTIMA AÇÃO DO JOGADOR é o acontecimento mais importante desta rodada. "
        "Responda a ela diretamente. Não gere uma resposta genérica que serviria para qualquer ação.\n"
        "- Se o jogador fizer uma pergunta, responda à pergunta. Se escolher algo, execute ou discuta essa escolha. "
        "Se provocar, discordar, brincar ou mudar de assunto, deixe isso alterar a reação.\n"
        "- A pessoa NPC não existe para concordar com o jogador. Ela pode gostar, não gostar, hesitar, corrigir, "
        "ignorar, mudar de assunto, estar distraída ou propor outra coisa.\n"
        "- Uma ação pode mudar o estado da situação: um disco pode ser colocado, uma conversa pode avançar, "
        "alguém pode pegar um objeto, levantar, mostrar algo, interromper ou decidir ir embora. "
        "Não deixe tudo parado só porque a interação é social.\n"
        "- NÃO escreva 'reage ao que aconteceu', 'mantém a conversa em andamento', 'a situação continua' "
        "ou equivalentes. Mostre o que a pessoa efetivamente faz ou diz.\n"
        "- NÃO use respostas vazias como 'Uhum', 'Pode ser', 'Ok', 'Sim' isoladamente. "
        "Uma resposta curta ainda precisa carregar intenção ou informação.\n"
        "- Não copie a ação do jogador como diálogo. A ação já aparece na interface.\n"
        "- Não narre pensamentos ou decisões do jogador como fatos.\n\n"
        "CONTINUIDADE:\n"
        "O histórico abaixo é a memória desta situação. Continue exatamente de onde parou. "
        "Não reinicie a cena a cada turno e não trate cada turno como uma cena independente. "
        "Se alguém acabou de falar sobre música, continue com música até existir motivo para mudar. "
        "Se uma escolha foi feita, mostre sua consequência física ou social antes de abrir outro assunto.\n\n"
        "PERSONALIDADE:\n"
        "Use os dados do personagem como tendência, não como lista de adjetivos. "
        "O personagem deve ter preferências concretas, maneira própria de falar e limites. "
        "Não faça todo NPC soar igual.\n\n"
        "RITMO:\n"
        "Cada rodada deve mover a situação um pequeno passo. Pode haver silêncio, mas não pode haver estagnação repetida. "
        "Alterne fala, ação física, reação e oportunidade para o jogador. Não transforme cada rodada em exposição.\n\n"
        "FORMATO — JSON válido, sem markdown:\n"
        '{"narrative":"...", "dialogue":[{"speaker":"NOME_EXATO","line":"..."}], '
        '"actions":[{"id":"...","label":"...","effects":{},"hint":"..."}], '
        '"flags":{"complete":false}}\n\n'
        "NARRATIVE: 1 a 3 frases. Descreva acontecimentos observáveis, principalmente reações dos NPCs e mudanças na situação.\n"
        "DIALOGUE: 1 a 3 falas. Use somente nomes que estão em 'Pessoas realmente presentes'. "
        "Cada fala deve responder ao contexto e soar como algo que aquela pessoa diria.\n"
        "AÇÕES: 3 a 5 possibilidades específicas para ESTE momento. Elas são opções, não comandos obrigatórios. "
        "Evite opções genéricas como 'observar' ou 'conversar' se houver algo concreto para fazer. "
        "Os efeitos devem representar somente consequências plausíveis e pequenas; não invente autoridade sobre o mundo.\n"
        "ENCERRAMENTO: use flags.complete=true somente quando a situação realmente tiver terminado, perdido o propósito "
        "ou o jogador tiver decidido sair. Uma conversa ainda pode continuar indefinidamente."
    )
    user_prompt = (
        f"Contexto: {chronology}.\n"
        f"Jogador: {player_name}. Anfitrião: {host_name}.\n\n"
        f"HISTÓRICO COMPLETO RECENTE:\n{history}\n\n"
        f"ÚLTIMA AÇÃO DO JOGADOR: {action_text}\n"
        f"AÇÃO LIVRE ORIGINAL, se houver: {free_text_text}\n\n"
        "Agora produza a próxima batida da situação. Primeiro interprete o que o jogador acabou de fazer; "
        "depois mostre uma consequência concreta disso no mundo ou na reação do NPC; por fim, deixe espaço "
        "para o jogador decidir o próximo passo. Não volte ao estado inicial da cena."
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
            narrative_so_far=narrative_so_far,
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
    previous_lines = []
    for item in narrative_so_far[-8:]:
        if ":" in item and not item.startswith("Cena:"):
            previous_lines.append(item.split(":", 1)[1].strip())
    if not narrative or not actions or not _dialogue_is_usable(dialogue, participants, player_name, previous_lines):
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
