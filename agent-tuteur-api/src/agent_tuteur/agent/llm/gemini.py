"""Fournisseur Gemini (API Google), entièrement asynchrone.

``POST .../models/{modèle}:generateContent`` avec la clé en en-tête
``x-goog-api-key``. Le streaming passe par ``:streamGenerateContent?alt=sse``,
consommé par ``httpx.AsyncClient``.

**Pourquoi httpx et non le SDK ``google-generativeai``** (celui qu'utilise NURU) :
ce SDK est **synchrone**. Chaque appel bloquerait la boucle événementielle du
serveur, et donc *toutes* les autres requêtes en cours, le temps de la
génération — plusieurs secondes. Il n'expose pas non plus de streaming
asynchrone exploitable par le flux SSE de l'API. On reprend donc la même
approche que ``mistral.py``, avec laquelle ce module est volontairement
symétrique.

Comme les autres fournisseurs, toute erreur (clé absente, HTTP, réseau, réponse
inattendue) devient une ``LLMError``, ce qui laisse la chaîne de repli basculer
vers le fournisseur suivant.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from agent_tuteur.agent.llm.base import BaseLLM, LLMError

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class GeminiLLM(BaseLLM):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._api_key = api_key
        self._model = model

    def available(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise LLMError("GEMINI_API_KEY manquante.")
        return {"x-goog-api-key": self._api_key, "Content-Type": "application/json"}

    def _payload(self, prompt: str, system: str | None) -> dict:
        """Corps de requête Gemini.

        La consigne système a son propre champ (``systemInstruction``) et n'est
        pas un message comme chez Mistral : la glisser dans ``contents`` la
        ferait passer pour une réplique de l'élève.
        """
        payload: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    def _url(self, methode: str, *, stream: bool = False) -> str:
        suffixe = "?alt=sse" if stream else ""
        return f"{_BASE_URL}/{self._model}:{methode}{suffixe}"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    self._url("generateContent"),
                    headers=self._headers(),
                    json=self._payload(prompt, system),
                )
                resp.raise_for_status()
                return _extraire_texte(resp.json())
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
            raise LLMError(f"Gemini generate a échoué : {exc}") from exc

    async def generate_stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    self._url("streamGenerateContent", stream=True),
                    headers=self._headers(),
                    json=self._payload(prompt, system),
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        fragment = _parse_ligne_sse(line)
                        if fragment is not None:
                            yield fragment
        except httpx.HTTPError as exc:
            raise LLMError(f"Gemini stream a échoué : {exc}") from exc


def _extraire_texte(data: dict) -> str:
    """Texte d'une réponse Gemini complète.

    Une réponse peut légitimement ne contenir aucun candidat — par exemple quand
    le filtre de sécurité de Google a tout bloqué. C'est une ``LLMError`` (donc
    un basculement vers le fournisseur suivant), pas une chaîne vide rendue à
    l'élève.
    """
    candidats = data.get("candidates") or []
    if not candidats:
        raison = data.get("promptFeedback", {}).get("blockReason", "aucun candidat")
        raise LLMError(f"Gemini n'a rien renvoyé ({raison}).")
    parts = candidats[0].get("content", {}).get("parts") or []
    texte = "".join(p.get("text", "") for p in parts)
    if not texte:
        raise LLMError("Gemini a renvoyé une réponse vide.")
    return texte


def _parse_ligne_sse(line: str) -> str | None:
    """Extrait le fragment de texte d'une ligne SSE Gemini.

    Renvoie ``None`` pour tout ce qui n'est pas un fragment exploitable (ligne
    vide, séparateur, réponse partielle sans texte) : c'est du bruit de
    protocole, pas une erreur.
    """
    if not line or not line.startswith("data:"):
        return None
    data = line[len("data:"):].strip()
    if not data:
        return None
    try:
        parts = json.loads(data)["candidates"][0]["content"]["parts"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None
    return "".join(p.get("text", "") for p in parts) or None
