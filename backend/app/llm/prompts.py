from __future__ import annotations

from app.llm.base import LLMError


def build_dialogue_prompt(
    *,
    npc_name: str,
    npc_role: str,
    npc_bio: str,
    npc_style: str,
    npc_personality: dict,
    npc_likes: list,
    npc_dislikes: list,
    npc_hobbies: list,
    npc_goals: list,
    player_name: str,
    world: dict,
    recent_messages: list[tuple[str, str]],
) -> tuple[str, str]:
    likes = ", ".join(npc_likes) or "não especificado"
    dislikes = ", ".join(npc_dislikes) or "não especificado"
    hobbies = ", ".join(npc_hobbies) or "não especificado"
    goals = "; ".join(npc_goals) or "nenhum objetivo explícito"

    system_prompt = (
        f"Você interpreta {npc_name}, morador(a) da Vila Serena, uma cidade pequena brasileira "
        f"numa rede social. SEMPRE responda em português do Brasil, em no máximo 3 frases curtas, "
        "como se estivesse mandando mensagem de celular, sem emojis em excesso (no máximo 1) e "
        "sem sair do personagem.\n"
        f"Quem você é: {npc_role}. Bio: {npc_bio}.\n"
        f"Personalidade: {npc_personality}. Tom: {npc_style}.\n"
        f"Gosta de: {likes}. Não gosta de: {dislikes}.\n"
        f"Hobbies: {hobbies}. Objetivos: {goals}.\n"
        "Regras: não quebre a ficção nem fale sobre o sistema; trate o jogador como um antigo "
        "ou novo conhecido; demonstre memória do que já foi dito na conversa; seja coerente com "
        "sua rotina e humor."
    )

    chrono = f"{world.get('day_name', '')}, dia {world.get('date', '')} às {world.get('time', '')}."
    history = "\n".join(
        f"{sender}: {text}" for sender, text in recent_messages[-12:]
    ) or "(vocês acabaram de se conhecer)"
    user_prompt = (
        f"Contexto: {chrono}\n\n"
        f"Fala de {player_name}: você está conversando por mensagem com {npc_name}.\n\n"
        f"Histórico recente:\n{history}\n\n"
        f"Agora responda COMO {npc_name} (apenas a fala, sem introduções como 'Claro', "
        "sem aspas e sem nomes de quem faz a pergunta)."
    )
    return system_prompt, user_prompt


def build_post_prompt(
    *,
    npc_name: str,
    npc_role: str,
    npc_personality: dict,
    npc_hobbies: list,
    world: dict,
) -> tuple[str, str]:
    hobbies = ", ".join(npc_hobbies) or "coisas simples da cidade"
    system_prompt = (
        f"Você interpreta {npc_name}, morador(a) de Vila Serena. Publique UM post autoral em "
        f"português do Brasil, estilo rede social da cidade (como o Facebook de uma cidade pequena), "
        "entre 10 e 35 palavras, sem hashtags, sem emojis demais (no máximo 1) e sem quebrar a "
        f"fictionalização do personagem. Personalidade: {npc_personality}.\n"
        f"Você gosta de: {hobbies}.\n"
        "Escreva algo que essa pessoa realmente publicaria no dia de hoje, considerando a rotina dela."
    )
    user_prompt = (
        f"Hora agora em Vila Serena: {world.get('day_name', '')}, dia {world.get('date', '')} às "
        f"{world.get('time', '')}.\n\nPublique o post agora."
    )
    return system_prompt, user_prompt


def build_comment_prompt(
    *,
    npc_name: str,
    npc_personality: dict,
    post_content: str,
    post_author: str,
    world: dict,
) -> tuple[str, str]:
    system_prompt = (
        f"Você interpreta {npc_name}, morador(a) de Vila Serena. Comente um post de outro morador "
        "em português do Brasil, como quem responde na timeline de uma cidade pequena: 1 frase "
        "curta e natural, sem hashtags e sem emojis demais (no máximo 1), sem quebrar o personagem. "
        f"Personalidade: {npc_personality}.\n"
        "Não responda esta instrução; escreva apenas o comentário."
    )
    user_prompt = (
        f"{post_author} publicou: \"{post_content}\"\n"
        f"(agora em Vila Serena: {world.get('day_name', '')}, dia {world.get('date', '')} às "
        f"{world.get('time', '')}).\n\nEscreva seu comentário."
    )
    return system_prompt, user_prompt


async def complete_with_timeout(
    provider, *, system_prompt, user_prompt, personality, model: str | None = None, timeout: float = 20.0
) -> str:
    import asyncio

    from app.llm.base import LLMProvider

    assert isinstance(provider, LLMProvider)
    try:
        return await asyncio.wait_for(
            provider.complete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                personality=personality,
                model=model,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError as exc:
        raise LLMError("A resposta do morador demorou demais.") from exc