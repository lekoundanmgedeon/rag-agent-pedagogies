from collections.abc import AsyncIterator

import pytest

from agent_tuteur.agent.llm.base import BaseLLM, LLMError
from agent_tuteur.agent.llm.mock import MockLLM
from agent_tuteur.agent.llm.router import FallbackRouter, build_router


class _Failing(BaseLLM):
    """Fournisseur simulant une panne (Mistral indisponible)."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def generate(self, prompt, *, system=None):
        raise LLMError(f"{self.name} indisponible")

    async def generate_stream(self, prompt, *, system=None) -> AsyncIterator[str]:
        raise LLMError(f"{self.name} indisponible")
        yield  # pragma: no cover


class _Working(BaseLLM):
    def __init__(self, name: str, text: str) -> None:
        self.name = name
        self._text = text

    async def generate(self, prompt, *, system=None):
        return self._text

    async def generate_stream(self, prompt, *, system=None) -> AsyncIterator[str]:
        for word in self._text.split():
            yield word + " "


async def test_mistral_ko_falls_back_to_ollama():
    router = FallbackRouter([_Failing("mistral"), _Working("ollama", "réponse locale"), MockLLM()])
    assert await router.generate("q") == "réponse locale"
    assert router.last_used == "ollama"


async def test_all_fail_except_mock():
    router = FallbackRouter([_Failing("mistral"), _Failing("ollama"), MockLLM()])
    out = await router.generate("q")
    assert "démonstration" in out
    assert router.last_used == "mock"


async def test_streaming_falls_back_before_first_token():
    router = FallbackRouter([_Failing("mistral"), _Working("ollama", "bonjour élève")])
    tokens = [tok async for tok in router.generate_stream("q")]
    assert "".join(tokens).strip() == "bonjour élève"
    assert router.last_used == "ollama"


def test_build_router_chain_with_mistral_key():
    router = build_router(backend="auto", mistral_api_key="sk-xxx")
    assert router.chain == ["mistral", "ollama", "mock"]


def test_build_router_defaults_to_mock_offline():
    # Pas de clé Mistral et sonde Ollama désactivée -> uniquement le mock.
    router = build_router(backend="auto", mistral_api_key="", probe_ollama=False)
    assert router.chain == ["mock"]


def test_build_router_explicit_mock():
    assert build_router(backend="mock").chain == ["mock"]
