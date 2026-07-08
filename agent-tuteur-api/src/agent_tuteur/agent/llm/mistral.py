"""Fournisseur Mistral (API primaire), entièrement asynchrone.

POST ``https://api.mistral.ai/v1/chat/completions`` avec authentification Bearer.
Streaming via SSE (``stream=true``), consommé par ``httpx.AsyncClient`` pour ne
jamais bloquer la boucle événementielle FastAPI. Toute erreur (clé absente,
HTTP, réseau) est convertie en ``LLMError`` pour laisser le routeur de fallback
basculer.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from agent_tuteur.agent.llm.base import BaseLLM, LLMError

_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class MistralLLM(BaseLLM):
    name = "mistral"

    def __init__(self, api_key: str, model: str = "mistral-small-latest") -> None:
        self._api_key = api_key
        self._model = model

    def available(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise LLMError("MISTRAL_API_KEY manquante.")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _messages(self, prompt: str, system: str | None) -> list[dict]:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        payload = {"model": self._model, "messages": self._messages(prompt, system), "stream": False}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(_ENDPOINT, headers=self._headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"Mistral generate a échoué : {exc}") from exc

    async def generate_stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        payload = {"model": self._model, "messages": self._messages(prompt, system), "stream": True}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream(
                    "POST", _ENDPOINT, headers=self._headers(), json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        token = _parse_sse_line(line)
                        if token is not None:
                            yield token
        except httpx.HTTPError as exc:
            raise LLMError(f"Mistral stream a échoué : {exc}") from exc


def _parse_sse_line(line: str) -> str | None:
    """Extrait le fragment de contenu d'une ligne SSE OpenAI-compatible."""
    if not line or not line.startswith("data:"):
        return None
    data = line[len("data:"):].strip()
    if data == "[DONE]" or not data:
        return None
    try:
        delta = json.loads(data)["choices"][0]["delta"]
    except (json.JSONDecodeError, KeyError, IndexError):
        return None
    return delta.get("content") or None
