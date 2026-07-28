"""Configuration centrale, chargée depuis l'environnement (.env).

Le cœur métier lit ses réglages ici plutôt que d'accéder directement à
``os.environ`` : une seule source de vérité, testable et surchargée facilement.
Tous les défauts permettent un premier lancement *hors-ligne* (backends légers,
LLM mock) sans aucune infrastructure.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EmbeddingBackend = Literal["light", "bge_m3"]
VectorBackend = Literal["memory", "qdrant"]
LLMBackend = Literal["auto", "mistral", "ollama", "mock"]


class Settings(BaseSettings):
    """Réglages applicatifs. Insensible à la casse, ignore les clés inconnues."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Persistance / queue (couches externes, étapes 4+) ---
    database_url: str = "postgresql+asyncpg://tuteur:tuteur@localhost:5432/tuteur"
    redis_url: str = "redis://localhost:6379/0"

    # --- Vecteurs ---
    vector_backend: VectorBackend = "memory"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "curriculum"

    # --- Embeddings ---
    embedding_backend: EmbeddingBackend = "light"
    embedding_dense_dim: int = 256

    # --- LLM ---
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    llm_backend: LLMBackend = "auto"

    # --- API / tenant ---
    api_base_url: str = "http://localhost:8000"
    max_file_size_mb: int = 25
    default_tenant: str = "default"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 168  # 7 jours — durée de vie du jeton de session
    cors_origins: str = "*"  # liste séparée par des virgules, ou "*" (dev)
    rate_limit_chat: str = "20/minute"
    rate_limit_upload: str = "10/minute"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # --- RAG ---
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    rrf_k: int = Field(default=60, ge=1)


@lru_cache
def get_settings() -> Settings:
    """Instance mémoïsée (évite de relire l'environnement à chaque appel)."""
    return Settings()
