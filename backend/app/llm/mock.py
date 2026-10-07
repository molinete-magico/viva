from app.llm.base import LLMProvider
from app.llm.prompts import build_dialogue_prompt


class MockLLMProvider(LLMProvider):
    """Provedor local, determinístico, usado quando não há chave de API configurada."""

    def __init__(self) -> None:
        self._count = 0

    async def complete(  # noqa: D102
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        personality: dict | None = None,
        model: str | None = None,
    ) -> str:
        self._count += 1
        energy = float((personality or {}).get("energy", 0.5))
        style = (personality or {}).get("tone", "amigável")

        if model == "standard":
            return "Passei a tarde resolvendo coisas aqui pela Vila e o pessoal ajudou demais. Os desafios da cidade quem enfrenta é a gente mesmo."
        if self._count % 3 == 0:
            return "Ah, que bom te encontrar por aqui. Fico sempre de olho no que acontece na Vila Serena."
        if energy >= 0.7:
            return "Olha quem apareceu! Vamos, conta — o que anda rolando com você por aí?"
        if style in {"sereno", "quieto", "poética", "afável", "maternal"}:
            return "Fala baixinho, mas de coração: sempre dá para trocar uma ideia boa nessa cidade."
        return "Puxa, que bom você por perto. O que acha de a gente conversar um pouco mais?"

    async def health(self) -> bool:
        return True