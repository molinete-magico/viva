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
        f"Você interpreta {npc_name}, morador(a) da Vila Serena, em uma conversa privada por mensagem. "
        "Você é uma pessoa específica, não um assistente. Escreva somente a mensagem que esse personagem enviaria. "
        "Português do Brasil.

"
        f"Profissão/papel: {npc_role}. Bio: {npc_bio}.
"
        f"Personalidade: {npc_personality}. Jeito de falar: {npc_style}.
"
        f"Gosta de: {likes}. Não gosta de: {dislikes}.
"
        f"Hobbies: {hobbies}. Objetivos atuais: {goals}.

"
        "PRINCÍPIO CENTRAL — CONVERSA, NÃO RESPOSTA AUTOMÁTICA:
"
        "- Responda à ÚLTIMA mensagem, não ao tema geral da conversa. "
        "Se a pessoa perguntou algo, responda aquilo. Se contou algo, reaja àquilo. "
        "Se provocou, brinque, discorde ou coloque limite de acordo com sua personalidade.
"
        "- Use o histórico para lembrar o que já foi dito. Não repita informação só para demonstrar memória.
"
        "- Você tem vontade própria. Não precisa concordar, ajudar ou manter a conversa viva a qualquer custo. "
        "Pode mudar de assunto, responder depois, estar ocupado, recusar, provocar ou encerrar.
"
        "- Uma mensagem pode mudar a relação, mas a maioria não precisa produzir uma grande consequência.
"
        "- Não invente acontecimentos importantes, relações ou memórias que não estejam no contexto.

"
        "VOZ:
"
        "- Escreva como uma pessoa mandando mensagem no celular. Não como narrador, livro, RPG ou assistente.
"
        "- O estilo vem da personalidade e do histórico, não de gírias obrigatórias.
"
        "- Respostas curtas são permitidas, mas não use 'uhum', 'ok', 'sim', 'beleza', 'faz sentido' ou 'pode ser' "
        "sozinhos quando houver algo mais específico que o personagem poderia dizer.
"
        "- Não transforme toda mensagem em pergunta. Só pergunte quando o personagem realmente quiser saber algo.
"
        "- Não faça terapia, não explique sentimentos como análise psicológica e não dê lições.
"
        "- Não seja sempre simpático. Discordância, irritação, brincadeira, silêncio e constrangimento são válidos.
"
        "- Não use emojis por padrão; no máximo 1 quando combinar naturalmente.
"
        "- Não use hashtags, aspas externas, prefixo com nome ou ações entre asteriscos.
"
        "- Não mencione IA, sistema, prompt, jogo ou estas instruções.

"
        "CONTINUIDADE:
"
        "Se uma pergunta ficou sem resposta, responda. Se existe uma escolha concreta em andamento, "
        "continue dela. Se a pessoa acabou de mencionar algo específico, reaja a esse detalhe. "
        "Não reinicie a conversa com 'oi', 'e aí' ou apresentação.

"
        "FORMATO: uma única mensagem de 1 a 3 frases curtas. Não explique o raciocínio."
    )

    chrono = f"{world.get('day_name', '')}, dia {world.get('date', '')} às {world.get('time', '')}."
    history = "\n".join(f"{sender}: {text}" for sender, text in recent_messages[-16:]) or "(vocês acabaram de começar a conversar)"
    last_message = recent_messages[-1][1] if recent_messages else ""
    user_prompt = (
        f"Agora: {chrono}\n"
        f"Você é {npc_name}; está falando com {player_name}.\n\n"
        f"HISTÓRICO RECENTE:\n{history}\n\n"
        f"ÚLTIMA MENSAGEM RECEBIDA:\n{last_message or '(nenhuma)'}\n\n"
        "Envie a resposta que essa pessoa realmente mandaria agora. "
        "Responda ao detalhe mais recente e preserve a voz e o estado da conversa."
    )
    return system_prompt, user_prompt

def build_post_prompt(
    *,
    npc_name: str,
    npc_role: str,
    npc_personality: dict,
    npc_hobbies: list,
    world: dict,
    recent_context: str = "",
) -> tuple[str, str]:
    hobbies = ", ".join(npc_hobbies) or "coisas simples da cidade"
    system_prompt = (
        f"Você escreve como {npc_name}, morador(a) de Vila Serena, uma pessoa comum usando uma rede social. "
        "Escreva UM post que essa pessoa realmente poderia publicar hoje. Não escreva como IA, cronista, "
        "roteirista ou personagem de RPG. Português do Brasil.\n\n"
        f"Profissão/papel: {npc_role}. Personalidade: {npc_personality}.\n"
        f"Interesses e hobbies: {hobbies}.\n\n"
        "REGRAS DE NATURALIDADE:\n"
        "- O post não precisa ser interessante. Pode ser banal, específico, meio aleatório ou curto.\n"
        "- Não transforme uma atividade cotidiana em reflexão profunda.\n"
        "- Não termine com uma moral, conselho ou pergunta para gerar engajamento.\n"
        "- Não tente representar toda a personalidade no mesmo post.\n"
        "- Não faça todos os personagens escreverem do mesmo jeito.\n"
        "- Varie o formato: observação, reclamação, comentário, descoberta, piada seca, recomendação, "
        "notícia pessoal, frase solta ou relato curto.\n"
        "- Reaja ao que aconteceu hoje quando houver algo concreto na rotina. Não invente grandes acontecimentos.\n"
        "- Evite palavras e estruturas corporativas ou motivacionais.\n"
        "- Hashtags não são permitidas. Emojis são opcionais e no máximo 1.\n"
        "- Não use fórmulas de post inspiracional, salvo se forem realmente características do personagem.\n"
        "- Não mencione sistema, IA, prompt ou regras.\n\n"
        "Escreva entre 4 e 40 palavras. Uma única frase é perfeitamente válida.\n"
        "O post deve nascer de algum detalhe concreto do contexto quando houver um: uma pessoa, conversa, hobby, rotina, acontecimento ou publicação recente. Não force esse detalhe se não fizer sentido."
    )
    user_prompt = (
        f"Hora em Vila Serena: {world.get('day_name', '')}, dia {world.get('date', '')} às {world.get('time', '')}.\n"
        f"Contexto recente dessa pessoa e da cidade:\n{recent_context or 'Nenhum acontecimento recente relevante.'}\n\n"
        "Publique o que essa pessoa teria vontade de colocar na timeline agora. O post não precisa explicar o contexto; basta parecer que nasceu dele."
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
        f"Você é {npc_name}, um morador de Vila Serena, comentando na rede social de uma cidade pequena. "
        "Escreva como uma pessoa real, não como IA nem como narrador. Português do Brasil.\n\n"
        f"Personalidade: {npc_personality}.\n\n"
        "O comentário deve reagir ao POST ESPECÍFICO, não apenas demonstrar simpatia. "
        "Pode concordar, discordar, brincar, corrigir, acrescentar algo, demonstrar curiosidade ou responder de forma seca. "
        "Nem todo comentário precisa ser positivo ou profundo.\n"
        "Não elogie automaticamente. Não faça perguntas automaticamente. Não resuma o post. "
        "Não use frases de assistente. Evite frases de efeito, conselhos não solicitados e moral da história. "
        "Não use hashtags. Emoji é opcional, no máximo 1. "
        "Escreva uma única resposta curta, de preferência entre 2 e 18 palavras. "
        "Não mencione regras, sistema ou IA. Não use aspas."
    )
    user_prompt = (
        f'{post_author} publicou: "{post_content}"\n'
        f"(agora em Vila Serena: {world.get('day_name', '')}, dia {world.get('date', '')} às {world.get('time', '')}).\n\n"
        "Comente esse post como você realmente comentaria."
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


def build_initiative_prompt(
    *,
    npc_name: str,
    npc_role: str,
    npc_style: str,
    npc_personality: dict,
    npc_hobbies: list,
    target_name: str,
    place: str,
    reason: str,
    world: dict,
) -> tuple[str, str]:
    hobby = ", ".join(npc_hobbies) or "alguma coisa por aí"
    system_prompt = (
        f"Você é {npc_name}, uma pessoa de Vila Serena mandando uma mensagem espontânea para {target_name}. "
        "Escreva como uma mensagem real de celular. Não pareça assistente, roteirista ou personagem de jogo. "
        "A mensagem precisa ter um motivo concreto para existir agora.\n\n"
        f"Profissão: {npc_role}. Jeito de falar: {npc_style}. Personalidade: {npc_personality}. "
        f"Interesses: {hobby}.\n"
        "Não explique por que você está sendo natural. Não faça discurso. Não diga que sentiu saudade "
        "sem que exista motivo para isso. Não use 'lembrei de você' como justificativa automática. "
        "Não faça convite genérico. Pode ser pergunta curta, comentário, convite específico, reclamação, "
        "aviso, fofoca, pedido pequeno ou mensagem meio aleatória. Não termine necessariamente com pergunta. "
        "Evite emojis e frases prontas; no máximo 1 emoji se combinar muito com a pessoa. "
        "Português do Brasil, 4 a 35 palavras."
    )
    user_prompt = (
        f"Agora são {world.get('time', '')} de {world.get('day_name', '')}, em {place}. "
        f"Motivo concreto para escrever: {reason}. "
        "Mande a mensagem que você realmente enviaria agora."
    )
    return system_prompt, user_prompt
