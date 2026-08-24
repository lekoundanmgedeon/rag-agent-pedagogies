"""Fournisseur OpenAI (API primaire), entièrement asynchrone.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from agent_tuteur.agent.llm.base import BaseLLM, LLMError

_ENDPOINT = "https://api.openai.com/v1/chat/completions"
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class OpenAILLM(BaseLLM):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-5.5") -> None:
        self._api_key = api_key
        self._model = model

    def available(self) -> bool:
        return bool(self._api_key)

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        if not self._api_key:
            raise LLMError("Clé API manquante")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(_ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise LLMError(f"Erreur HTTP: {exc}") from exc
        except (KeyError, ValueError) as exc:
            raise LLMError(f"Réponse malformée: {exc}") from exc

    async def generate_stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        if not self._api_key:
            raise LLMError("Clé API manquante")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.3,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream("POST", _ENDPOINT, json=payload, headers=headers) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue
        except httpx.HTTPError as exc:
            raise LLMError(f"Erreur HTTP: {exc}") from exc
