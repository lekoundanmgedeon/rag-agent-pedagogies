"""Fournisseur Ollama (fallback local souverain), entièrement asynchrone.

POST ``{OLLAMA_BASE_URL}/api/chat`` avec ``stream=true``. Si le serveur est
absent, l'erreur réseau devient une ``LLMError`` propre pour laisser la chaîne de
fallback basculer vers le mock.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from agent_tuteur.agent.llm.base import BaseLLM, LLMError

_TIMEOUT = httpx.Timeout(120.0, connect=3.0)


class OllamaLLM(BaseLLM):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen3:8b") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def available(self) -> bool:
        """Ping léger de ``/api/tags`` : le serveur répond-il ?

        Reste synchrone : n'est appelée qu'au démarrage (composition du routeur
        de fallback), jamais dans le chemin chaud d'une requête.
        """
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=httpx.Timeout(2.0))
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

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
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"Ollama generate a échoué : {exc}") from exc

    async def generate_stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        payload = {"model": self._model, "messages": self._messages(prompt, system), "stream": True}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream("POST", f"{self._base_url}/api/chat", json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        token = chunk.get("message", {}).get("content")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama stream a échoué : {exc}") from exc
