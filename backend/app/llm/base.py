from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(Exception):
    """Erro de infraestrutura/API do provedor de LLM (nunca um erro de domínio)."""


class RateLimitError(LLMError):
    """Limite de uso da API atingido (ex.: 429 no Groq)."""


class LLMReply:
    def __init__(self, text: str) -> None:
        self.text = text.strip().strip('"\u201c\u201d')


LLM_TIER_QUICK = "quick"
LLM_TIER_STANDARD = "standard"


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        personality: dict | None = None,
        model: str | None = None,
    ) -> str:
        """Retorna a fala do personagem ou levanta LLMError.

        `model` pode ser um tier (`quick`, `standard`) ou um ID de modelo explícito.
        """

    @abstractmethod
    async def health(self) -> bool:
        """True se o provedor está configurado e alcançável."""