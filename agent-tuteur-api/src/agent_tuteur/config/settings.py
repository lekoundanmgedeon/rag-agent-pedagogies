"""Configuration centrale, chargée depuis l'environnement (.env).

Le cœur métier lit ses réglages ici plutôt que d'accéder directement à
``os.environ`` : une seule source de vérité, testable et surchargée facilement.
Tous les défauts permettent un premier lancement *hors-ligne* (backends légers,
LLM mock) sans aucune infrastructure.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

EmbeddingBackend = Literal["light", "bge_m3"]
VectorBackend = Literal["memory", "qdrant"]
LLMBackend = Literal["auto", "mistral", "gemini", "ollama", "mock"]


def _vide_vaut_absent(valeur):
    """``CLE=`` dans un ``.env`` vaut « non renseigné », pas « chaîne vide ».

    Sans cela, un réglage optionnel laissé vide dans ``.env.example`` fait
    échouer le démarrage sur une erreur de conversion — un fichier d'exemple
    doit pouvoir être copié tel quel.
    """
    return None if isinstance(valeur, str) and not valeur.strip() else valeur


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
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.5"
    llm_juge_model: str = "gemini-3.1-pro"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    llm_backend: LLMBackend = "auto"
    #: Ordre explicite de la chaîne de repli, ex. ``"gemini,mistral,mock"``.
    #: Vide = composition automatique selon les clés disponibles. Renseigné, il
    #: l'emporte sur ``llm_backend`` : changer de fournisseur principal devient
    #: un réglage de `.env`, sans modification de code ni redéploiement.
    llm_chain: str = ""

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

    # Répertoire du build statique du SPA Vue (`agent-tuteur-web/dist`). Vide par
    # défaut : en dev comme en Docker Compose, c'est nginx qui sert le SPA et
    # l'API n'expose que /api + /health. Renseigné uniquement dans l'image
    # mono-conteneur, où FastAPI sert aussi le frontend (cf. api.main._mount_spa).
    spa_dist_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # --- RAG ---
    retrieval_top_k: int = Field(default=5, ge=1, le=50)
    rrf_k: int = Field(default=60, ge=1)
    #: Cosinus dense minimal pour qu'un extrait soit servi (cas QA #5, règle
    #: non-négociable n°4). Vide = celui de l'embedder, qui seul connaît son
    #: espace vectoriel — c'est le cas normal. Ce réglage n'existe que pour
    #: réajuster la valeur en exploitation sans redéployer, une fois la mesure
    #: refaite sur l'index réel ; il ne sert pas à en inventer une là où
    #: l'embedder déclare qu'aucun seuil n'est posable (« light »).
    rag_seuil_pertinence: Annotated[float | None, BeforeValidator(_vide_vaut_absent)] = Field(
        default=None, ge=-1.0, le=1.0
    )
    #: Fraction du top-k devant se porter sur un même chapitre pour que la
    #: question soit jugée dans le périmètre du corpus (cas QA #5). Vide = celle
    #: de l'embedder, qui est le cas normal — c'est de sa qualité sémantique que
    #: la règle dépend, pas d'une préférence d'application. Ce réglage existe
    #: pour resserrer ou desserrer le périmètre en exploitation sans redéployer,
    #: une fois la mesure refaite sur l'index réel.
    rag_consensus_chapitre: Annotated[float | None, BeforeValidator(_vide_vaut_absent)] = Field(
        default=None, gt=0.0, le=1.0
    )


@lru_cache
def get_settings() -> Settings:
    """Instance mémoïsée (évite de relire l'environnement à chaque appel)."""
    return Settings()
