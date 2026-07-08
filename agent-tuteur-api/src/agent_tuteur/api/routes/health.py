"""GET /health — sondes db, redis, qdrant, llm.

``redis`` reflète l'état du pool ARQ construit au lifespan
(``app.state.arq_pool``) : ``"ok"`` s'il est disponible, ``"degraded"`` s'il
est absent (repli automatique de l'ingestion sur ``BackgroundTasks`` — mode
dégradé assumé, pas une panne signalée en ``status: degraded`` global). Qdrant
n'est sondé que si ``VECTOR_BACKEND=qdrant`` ; en mode ``memory`` (défaut), il
n'y a pas de serveur à vérifier.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text

from agent_tuteur.api.schemas import HealthOut
from agent_tuteur.config.settings import get_settings
from agent_tuteur.persistence.db import get_engine

router = APIRouter(tags=["health"])


async def _check_db() -> bool:
    try:
        engine = get_engine()
    except RuntimeError:
        return False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — une sonde de santé ne doit jamais lever.
        return False


@router.get("/health", response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    settings = get_settings()
    db_ok = await _check_db()

    qdrant_status = "not_configured"
    if settings.vector_backend == "qdrant":
        indexer = getattr(request.app.state, "indexer", None)
        try:
            if indexer is not None:
                indexer.count()  # sonde légère : lève si le serveur est injoignable
            qdrant_status = "ok"
        except Exception:  # noqa: BLE001 — une sonde de santé ne doit jamais lever.
            qdrant_status = "unreachable"

    agent = getattr(request.app.state, "agent", None)
    llm_chain = agent.llm_chain if agent is not None else []

    redis_status = "ok" if getattr(request.app.state, "arq_pool", None) is not None else "degraded"

    status = "ok" if db_ok else "degraded"
    return HealthOut(
        status=status,
        db=db_ok,
        redis=redis_status,
        qdrant=qdrant_status,
        llm=llm_chain,
    )
