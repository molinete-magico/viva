from app.llm.base import LLMError, LLMProvider, RateLimitError

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLLMProvider(LLMProvider):
    """Provedor real via Groq Cloud (API compatível com OpenAI).

    Modelos: `quick` (padrão, gpt-oss-20b) para respostas rápidas e
    `standard` (gpt-oss-120b) para situações que merecem mais capricho.
    Um client httpx novo é criado por chamada para evitar reuso de loop
    de eventos entre chamadas separadas.
    """

    def __init__(self, api_key: str, quick: str | None = None, standard: str | None = None) -> None:
        self._api_key = api_key
        self._quick = quick or "openai/gpt-oss-20b"
        self._standard = standard or "openai/gpt-oss-120b"

    def resolve_model(self, model: str | None) -> str:
        if model in (None, "quick"):
            return self._quick
        if model == "standard":
            return self._standard
        return model

    async def complete(  # noqa: D102
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        personality: dict | None = None,
        model: str | None = None,
    ) -> str:
        import httpx

        resolved = self.resolve_model(model)
        payload = {
            "model": resolved,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.9,
            "max_tokens": 320,
        }

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(
                        GROQ_CHAT_URL,
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json=payload,
                    )
            except Exception as exc:  # noqa: BLE001
                raise LLMError(f"Groq indisponível: {exc}") from exc

            if response.status_code == 429:
                raise RateLimitError("O limite da API Groq foi atingido. Tente de novo em instantes.")
            if response.status_code >= 500 and attempt == 0:
                continue
            if response.status_code >= 400:
                detail = response.text[:300]
                raise LLMError(f"Groq respondeu {response.status_code}: {detail}")

            try:
                data = response.json()
                text = (data["choices"][0]["message"]["content"] or "").strip()
            except Exception as exc:  # noqa: BLE001
                raise LLMError(f"Resposta do Groq não veio como esperado: {exc}") from exc
            if not text and attempt == 0:
                continue
            if not text:
                raise LLMError("Groq respondeu vazio.")
            return text
        raise LLMError("Groq respondeu vazio.")

    async def health(self) -> bool:  # noqa: D102
        try:
            await self.complete(system_prompt="", user_prompt="diga apenas: ok", model="quick")
            return True
        except LLMError:
            return False