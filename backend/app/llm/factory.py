from app.config import settings
from app.llm.base import LLMProvider
from app.llm.groq import GroqLLMProvider
from app.llm.mock import MockLLMProvider

_provider: LLMProvider | None = None


def get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        if settings.groq_api_key:
            _provider = GroqLLMProvider(
                settings.groq_api_key,
                quick=settings.groq_model_quick,
                standard=settings.groq_model_standard,
            )
        else:
            _provider = MockLLMProvider()
    return _provider


def reset_provider() -> None:
    global _provider
    _provider = None