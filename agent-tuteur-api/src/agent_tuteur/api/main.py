"""Application FastAPI — assemblage (lifespan, CORS, rate limiting, routes).

Le ``lifespan`` construit une seule fois les singletons applicatifs (moteur DB,
stack RAG, LLM, agent) et les pose sur ``app.state`` ; les dépendances de
``api/dependencies.py`` se contentent de les lire. Aucune logique métier ici :
ce module ne fait que raccorder le cœur (``factory.py``) au monde HTTP.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from arq.connections import ArqRedis, RedisSettings, create_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.api.routes import chat, documents, feedback, health, progression, search
from agent_tuteur.config.settings import get_settings
from agent_tuteur.factory import build_llm, build_rag_stack, ingest_corpus
from agent_tuteur.persistence.db import dispose_engine, init_engine

CORPUS_DIR = Path(__file__).resolve().parents[3] / "corpus"


def _handle_rate_limit(request, exc):  # noqa: ANN001 - signature imposée par slowapi
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=429, content={"detail": "Trop de requêtes, réessayez plus tard."})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    init_engine(settings.database_url)

    rag_stack = build_rag_stack(settings)
    if settings.vector_backend == "memory" and rag_stack.indexer.count() == 0 and CORPUS_DIR.exists():
        # Amorce la démo : corpus d'exemple auto-ingéré dans le store in-memory
        # (vide à chaque redémarrage). Sans effet sur un backend Qdrant persistant.
        ingest_corpus(rag_stack.indexer, CORPUS_DIR)

    llm = build_llm(settings)
    agent = TutorAgent(rag_stack.retriever, llm, top_k=settings.retrieval_top_k)

    app.state.indexer = rag_stack.indexer
    app.state.retriever = rag_stack.retriever
    app.state.agent = agent

    # Pool ARQ optionnel : si Redis est injoignable, /api/upload se replie sur
    # un traitement en tâche de fond du même processus (dégradation gracieuse,
    # cf. api/routes/documents.py). Ne bloque jamais le démarrage de l'API.
    app.state.arq_pool = await _try_create_arq_pool(settings.redis_url)

    yield

    if app.state.arq_pool is not None:
        await app.state.arq_pool.aclose()
    await dispose_engine()


async def _try_create_arq_pool(redis_url: str) -> ArqRedis | None:
    settings = RedisSettings.from_dsn(redis_url)
    settings.conn_retries = 0  # échec immédiat si Redis est indisponible, pas de blocage au démarrage
    try:
        return await create_pool(settings)
    except Exception:  # noqa: BLE001 — Redis absent au démarrage : mode dégradé, pas une erreur fatale.
        return None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agent Tuteur Sénégal — API",
        description="Agent tuteur pédagogique RAG pour le programme scolaire sénégalais.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    app.include_router(progression.router)
    app.include_router(feedback.router)
    app.include_router(health.router)

    return app


app = create_app()
