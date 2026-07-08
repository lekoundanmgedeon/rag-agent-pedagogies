"""Chaîne de fallback LLM — bascule silencieuse à l'erreur (async).

Logique de composition :
* clé Mistral présente  → ``[Mistral, Ollama, Mock]`` ;
* sinon Ollama joignable → ``[Ollama, Mock]`` ;
* sinon                  → ``[Mock]``.

Le dernier maillon est toujours le mock : la génération ne bloque jamais. En
streaming, si un fournisseur échoue **avant** d'avoir émis le moindre token, on
passe au suivant ; s'il échoue après avoir déjà streamé, l'erreur est propagée
(impossible de rejouer proprement un flux partiel).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from agent_tuteur.agent.llm.base import BaseLLM, LLMError
from agent_tuteur.agent.llm.mock import MockLLM
from agent_tuteur.agent.llm.mistral import MistralLLM
from agent_tuteur.agent.llm.ollama import OllamaLLM


class FallbackRouter(BaseLLM):
    name = "fallback"

    def __init__(self, providers: list[BaseLLM]) -> None:
        if not providers:
            raise ValueError("Au moins un fournisseur est requis.")
        self._providers = providers

    @property
    def chain(self) -> list[str]:
        return [p.name for p in self._providers]

    #: Fournisseur effectivement utilisé lors du dernier appel (traçabilité).
    last_used: str | None = None

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        errors: list[str] = []
        for provider in self._providers:
            try:
                result = await provider.generate(prompt, system=system)
                self.last_used = provider.name
                return result
            except LLMError as exc:
                errors.append(f"{provider.name}: {exc}")
        raise LLMError("Tous les fournisseurs ont échoué : " + " | ".join(errors))

    async def generate_stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        errors: list[str] = []
        for provider in self._providers:
            produced = False
            try:
                async for token in provider.generate_stream(prompt, system=system):
                    produced = True
                    yield token
                self.last_used = provider.name
                return
            except LLMError as exc:
                if produced:
                    raise  # flux déjà entamé : pas de rejeu possible.
                errors.append(f"{provider.name}: {exc}")
        raise LLMError("Tous les fournisseurs ont échoué : " + " | ".join(errors))


def build_router(
    *,
    backend: str = "auto",
    mistral_api_key: str = "",
    mistral_model: str = "mistral-small-latest",
    ollama_base_url: str = "http://localhost:11434",
    ollama_model: str = "qwen3:8b",
    probe_ollama: bool = True,
) -> FallbackRouter:
    """Construit la chaîne de fallback selon la configuration et la disponibilité.

    ``available()`` reste synchrone (probe de démarrage), donc cette fabrique
    peut être appelée telle quelle depuis le lifespan FastAPI (hors event loop
    critique) sans nécessiter d'``await``.
    """
    mock = MockLLM()
    mistral = MistralLLM(mistral_api_key, mistral_model)
    ollama = OllamaLLM(ollama_base_url, ollama_model)

    if backend == "mock":
        return FallbackRouter([mock])
    if backend == "mistral":
        return FallbackRouter([mistral, mock])
    if backend == "ollama":
        return FallbackRouter([ollama, mock])

    # backend == "auto"
    if mistral_api_key:
        return FallbackRouter([mistral, ollama, mock])
    if probe_ollama and ollama.available():
        return FallbackRouter([ollama, mock])
    return FallbackRouter([mock])
