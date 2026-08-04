"""Chaîne de fallback LLM — bascule silencieuse à l'erreur (async).

**Ordre explicite** (recommandé) : ``LLM_CHAIN="gemini,mistral,mock"`` dans le
``.env`` impose la chaîne, sans toucher au code. Changer de fournisseur
principal devient un réglage réversible plutôt qu'une modification à
redéployer — c'est la réponse au point Q2 de la synthèse, qui laissait ouvert
l'arbitrage Gemini/Mistral.

**Composition automatique** (défaut, ``LLM_CHAIN`` vide) :
* clé Mistral présente  → ``[Mistral, Gemini, Ollama, Mock]`` ;
* sinon clé Gemini      → ``[Gemini, Ollama, Mock]`` ;
* sinon Ollama joignable → ``[Ollama, Mock]`` ;
* sinon                  → ``[Mock]``.

Le dernier maillon est **toujours** le mock : la génération ne bloque jamais.
C'est ce qui distingue cette approche de NURU, où l'absence de clé renvoyait à
l'élève un mode d'emploi de configuration au lieu d'une réponse.

En streaming, si un fournisseur échoue **avant** d'avoir émis le moindre token,
on passe au suivant ; s'il échoue après avoir déjà streamé, l'erreur est
propagée (impossible de rejouer proprement un flux partiel).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from agent_tuteur.agent.llm.base import BaseLLM, LLMError
from agent_tuteur.agent.llm.gemini import GeminiLLM
from agent_tuteur.agent.llm.mistral import MistralLLM
from agent_tuteur.agent.llm.mock import MockLLM
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
    chain: str = "",
    mistral_api_key: str = "",
    mistral_model: str = "mistral-small-latest",
    gemini_api_key: str = "",
    gemini_model: str = "gemini-2.5-flash",
    ollama_base_url: str = "http://localhost:11434",
    ollama_model: str = "qwen3:8b",
    probe_ollama: bool = True,
) -> FallbackRouter:
    """Construit la chaîne de fallback selon la configuration et la disponibilité.

    ``chain`` (ex. ``"gemini,mistral,mock"``) impose l'ordre et l'emporte sur
    ``backend``. Un nom inconnu y est ignoré plutôt que de faire échouer le
    démarrage : une faute de frappe dans un ``.env`` ne doit pas empêcher le
    service de répondre.

    ``available()`` reste synchrone (probe de démarrage), donc cette fabrique
    peut être appelée telle quelle depuis le lifespan FastAPI (hors event loop
    critique) sans nécessiter d'``await``.
    """
    mock = MockLLM()
    fournisseurs: dict[str, BaseLLM] = {
        "mistral": MistralLLM(mistral_api_key, mistral_model),
        "gemini": GeminiLLM(gemini_api_key, gemini_model),
        "ollama": OllamaLLM(ollama_base_url, ollama_model),
        "mock": mock,
    }

    if chain:
        noms = [n for nom in chain.split(",") if (n := nom.strip().lower()) in fournisseurs]
        # Le mock ferme toujours la marche, même si on l'a oublié dans le .env :
        # sans lui, une panne de tous les fournisseurs laisserait l'élève sans
        # aucune réponse.
        if "mock" not in noms:
            noms.append("mock")
        return FallbackRouter([fournisseurs[n] for n in noms])

    if backend in ("mistral", "gemini", "ollama"):
        return FallbackRouter([fournisseurs[backend], mock])
    if backend == "mock":
        return FallbackRouter([mock])

    # backend == "auto" : on compose selon les clés réellement disponibles.
    if mistral_api_key:
        chaine = [fournisseurs["mistral"]]
        if gemini_api_key:
            chaine.append(fournisseurs["gemini"])
        return FallbackRouter([*chaine, fournisseurs["ollama"], mock])
    if gemini_api_key:
        return FallbackRouter([fournisseurs["gemini"], fournisseurs["ollama"], mock])
    if probe_ollama and fournisseurs["ollama"].available():
        return FallbackRouter([fournisseurs["ollama"], mock])
    return FallbackRouter([mock])
