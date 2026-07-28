"""GET /health — sondes db, redis, qdrant, llm, cohérence des documents.

``redis`` reflète l'état du pool ARQ construit au lifespan
(``app.state.arq_pool``) : ``"ok"`` s'il est disponible, ``"degraded"`` s'il
est absent (repli automatique de l'ingestion sur ``BackgroundTasks`` — mode
dégradé assumé, pas une panne signalée en ``status: degraded`` global). Qdrant
n'est sondé que si ``VECTOR_BACKEND=qdrant`` ; en mode ``memory`` (défaut), il
n'y a pas de serveur à vérifier.

``documents_orphaned`` compte les documents déjà marqués ``orphaned`` (statut
persisté) pour le tenant courant — une requête COUNT bon marché, pas une
vérification live du vectorstore à chaque appel (coûteuse, réservée à
``POST /api/documents/verify-all``, appelé à la demande ou au démarrage).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from agent_tuteur.api.dependencies import get_optional_user
from agent_tuteur.api.schemas import HealthOut
from agent_tuteur.api.security import Principal
from agent_tuteur.config.settings import get_settings
from agent_tuteur.persistence.db import get_engine, session_scope
from agent_tuteur.persistence.repositories import DocumentRepository

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
async def health(
    request: Request,
    principal: Principal | None = Depends(get_optional_user),
) -> HealthOut:
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

    # Sonde publique de liveness : le compteur d'orphelins (par tenant) n'est
    # renseigné que si l'appelant est authentifié — sinon on ne connaît pas le tenant.
    orphaned_count = 0
    if principal is not None and db_ok:
        try:
            async with session_scope(principal.tenant_id) as session:
                orphaned_count = await DocumentRepository(session).count_by_status(
                    principal.tenant_id, "orphaned"
                )
        except Exception:  # noqa: BLE001 — une sonde de santé ne doit jamais lever.
            orphaned_count = 0

    status = "ok" if db_ok else "degraded"
    return HealthOut(
        status=status,
        db=db_ok,
        redis=redis_status,
        qdrant=qdrant_status,
        llm=llm_chain,
        documents_orphaned=orphaned_count,
    )
