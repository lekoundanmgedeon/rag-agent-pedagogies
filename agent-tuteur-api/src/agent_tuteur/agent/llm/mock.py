"""LLM *mock* — réponse pédagogique déterministe, sans réseau.

Dernier maillon de la chaîne de fallback : il ne doit **jamais** échouer, pour
qu'une démo ou un test tourne intégralement hors-ligne. La réponse reste dans la
posture socratique et reflète l'instruction d'indice présente dans le prompt.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

from agent_tuteur.agent.llm.base import BaseLLM

_HINT_MARKER = re.compile(r"Niveau d'indice\s*:\s*(\d)\s*\(([^)]+)\)", re.IGNORECASE)


class MockLLM(BaseLLM):
    name = "mock"

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        level, label = self._extract_hint(prompt)
        intro = "Voici comment je t'accompagne"
        if label:
            intro += f" (niveau « {label} »)"
        return (
            f"{intro} : reprenons ta question ensemble. "
            "D'après les extraits du cours, concentre-toi sur la notion clé, puis "
            "avance d'une étape à la fois. Quelle est, selon toi, la première chose "
            "à identifier ? [réponse générée en mode démonstration hors-ligne]"
        )

    async def generate_stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        # Streame mot par mot (espaces conservés) pour simuler un vrai flux.
        text = await self.generate(prompt, system=system)
        for token in re.findall(r"\S+\s*", text):
            yield token

    @staticmethod
    def _extract_hint(prompt: str) -> tuple[int | None, str | None]:
        match = _HINT_MARKER.search(prompt)
        if not match:
            return None, None
        return int(match.group(1)), match.group(2).strip()
