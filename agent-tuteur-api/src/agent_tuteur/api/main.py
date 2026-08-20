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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.api.routes import (
    auth,
    chat,
    conversations,
    documents,
    evaluation,
    feedback,
    health,
    logs,
    mastery,
    progression,
    quiz,
    search,
)
from agent_tuteur.api.routes.documents import verify_tenant_consistency
from agent_tuteur.config.settings import get_settings
from agent_tuteur.factory import build_llm_cours, build_llm_exercice, build_rag_stack, build_tool_registry, ingest_corpus
from agent_tuteur.observability import get_logger, log_event, setup_logging
from agent_tuteur.persistence.db import dispose_engine, init_engine, session_scope
from agent_tuteur.persistence.repositories import DocumentRepository

setup_logging("api")
_logger = get_logger("agent_tuteur.api.main")

CORPUS_DIR = Path(__file__).resolve().parents[3] / "corpus"


def _handle_rate_limit(request, exc):
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

    llm_cours = build_llm_cours(settings)
    llm_exercice = build_llm_exercice(settings)
    tool_registry = build_tool_registry()

    # --- Connexion MCP Math ---
    import sys
    from agent_tuteur.mcp.client import McpClient
    
    # On lance les serveurs MCP via la commande python courante
    math_mcp = McpClient(
        command=sys.executable,
        args=["-m", "agent_tuteur.mcp_servers.math_server"]
    )
    rag_mcp = McpClient(
        command=sys.executable,
        args=["-m", "agent_tuteur.mcp_servers.rag_server"]
    )
    try:
        await math_mcp.connect()
        await math_mcp.register_tools(tool_registry)
        _logger.info("Serveur MCP Math connecté.")
        
        await rag_mcp.connect()
        await rag_mcp.register_tools(tool_registry)
        _logger.info("Serveur MCP RAG connecté.")
    except Exception as e:
        _logger.error(f"Échec de connexion aux serveurs MCP : {e}")

    agent = TutorAgent(
        rag_stack.retriever,
        llm_cours=llm_cours,
        llm_exercice=llm_exercice,
        top_k=settings.retrieval_top_k,
        tool_registry=tool_registry,
    )

    app.state.indexer = rag_stack.indexer
    app.state.retriever = rag_stack.retriever
    app.state.agent = agent

    # Pool ARQ optionnel : si Redis est injoignable, /api/upload se replie sur
    # un traitement en tâche de fond du même processus (dégradation gracieuse,
    # cf. api/routes/documents.py). Ne bloque jamais le démarrage de l'API.
    app.state.arq_pool = await _try_create_arq_pool(settings.redis_url)

    await _check_consistency_best_effort(rag_stack.indexer, settings.default_tenant)

    yield

    if app.state.arq_pool is not None:
        await app.state.arq_pool.aclose()
    await dispose_engine()

    try:
        await math_mcp.disconnect()
        await rag_mcp.disconnect()
    except Exception:
        pass


async def _check_consistency_best_effort(indexer, default_tenant: str) -> None:
    """Vérifie au démarrage que les documents ``indexed`` du tenant par défaut
    ont bien des chunks dans le vectorstore actuel (détecte les orphelins créés
    par un changement de VECTOR_BACKEND ou un redémarrage entre deux sessions).
    Best-effort : ne doit jamais empêcher l'API de démarrer. Portée volontairement
    limitée au tenant par défaut (pas de scan multi-tenant au démarrage, coûteux
    et redondant avec ``POST /api/documents/verify-all`` disponible à la demande
    pour tout tenant).
    """
    try:
        async with session_scope(default_tenant) as session:
            repo = DocumentRepository(session)
            result = await verify_tenant_consistency(repo, indexer, default_tenant)
        if result.orphaned:
            log_event(
                _logger, "consistency:startup_check_found_orphans", log_level=30,
                tenant_id=default_tenant, checked=result.checked,
                orphaned_count=len(result.orphaned),
                orphaned_files=[o.filename for o in result.orphaned],
            )
    except Exception as exc:
        log_event(_logger, "consistency:startup_check_failed", log_level=30, error=str(exc))


async def _try_create_arq_pool(redis_url: str) -> ArqRedis | None:
    settings = RedisSettings.from_dsn(redis_url)
    settings.conn_retries = 0  # échec immédiat si Redis est indisponible, pas de blocage au démarrage
    try:
        return await create_pool(settings)
    except Exception:
        return None


def _mount_spa(app: FastAPI, dist_dir: str) -> None:
    """Sert le build statique du SPA Vue depuis l'API elle-même.

    Utilisé par un déploiement mono-conteneur : un seul service
    à déployer, donc même origine pour le SPA et l'API — pas de CORS, et le flux
    SSE de ``/api/chat`` n'est relayé par aucun proxy intermédiaire susceptible
    de le bufferiser. En dev et en Docker Compose, ``spa_dist_dir`` est vide et
    cette fonction ne fait rien (c'est nginx qui sert le SPA).

    La route attrape-tout doit rester déclarée **après** tous les routers, sinon
    elle masquerait les endpoints /api. Les chemins /api et /health non reconnus
    doivent répondre 404 (erreur d'API), pas ``index.html``.
    """
    root = Path(dist_dir).resolve()
    index = root / "index.html"
    if not index.is_file():
        log_event(_logger, "spa:dist_not_found", log_level=30, dist_dir=str(root))
        return

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def serve_spa(spa_path: str) -> FileResponse:
        if spa_path.startswith(("api/", "health")):
            raise HTTPException(status_code=404, detail="Not Found")
        if spa_path:
            candidate = (root / spa_path).resolve()
            # `is_relative_to` neutralise les remontées de chemin ("../..").
            if candidate.is_file() and candidate.is_relative_to(root):
                headers = (
                    # Les noms des assets Vite portent un hash de contenu :
                    # immuables, donc cachables agressivement.
                    {"Cache-Control": "public, max-age=31536000, immutable"}
                    if spa_path.startswith("assets/")
                    else None
                )
                return FileResponse(candidate, headers=headers)
        # Toute autre route est gérée côté client par vue-router.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    log_event(_logger, "spa:mounted", dist_dir=str(root))


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

    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    app.include_router(progression.router)
    # Domaine pédagogique porté de NURU (module 5 de la fusion).
    app.include_router(quiz.router)
    app.include_router(evaluation.router)
    app.include_router(mastery.router)
    app.include_router(feedback.router)
    app.include_router(health.router)
    app.include_router(logs.router)

    if settings.spa_dist_dir:
        _mount_spa(app, settings.spa_dist_dir)

    return app


app = create_app()
