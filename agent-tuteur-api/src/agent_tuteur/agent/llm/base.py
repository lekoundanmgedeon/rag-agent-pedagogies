"""Contrat commun des fournisseurs LLM (async).

Deux modes obligatoires : ``generate`` (réponse complète) et ``generate_stream``
(itérateur asynchrone de fragments, pour le streaming SSE de l'API). Le
découpage préparation/génération de l'agent s'appuie sur ce contrat : le cœur
assemble le prompt final (nœuds a→e), puis l'API streame ``generate_stream``
séparément — sans jamais bloquer la boucle événementielle FastAPI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class LLMError(RuntimeError):
    """Erreur d'un fournisseur LLM (indisponible, HTTP, réseau…)."""


class BaseLLM(ABC):
    #: Nom court, utile pour la traçabilité et /health.
    name: str = "base"

    @abstractmethod
    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Retourne la réponse complète pour un prompt assemblé."""

    @abstractmethod
    def generate_stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        """Streame la réponse fragment par fragment (générateur asynchrone)."""

    def available(self) -> bool:
        """Le fournisseur est-il utilisable ? (probe synchrone légère, sans exception).

        Reste synchrone à dessein : n'est appelée qu'à la construction du
        routeur de fallback (démarrage de l'app), jamais dans le chemin chaud
        d'une requête.
        """
        return True

    @property
    def chain(self) -> list[str]:
        """Chaîne de fallback effective (``/health``). Un seul maillon ici ;
        ``FallbackRouter`` la redéfinit pour exposer tous ses fournisseurs."""
        return [self.name]
