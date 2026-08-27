"""GET /api/catalogue — chapitres réellement indexés, pour l'accueil.

Le cas QA #28 est un décalage entre deux sources de vérité : l'écran d'accueil
proposait des sujets écrits en dur dans le frontend, pendant que l'agent, lui,
ne connaît que ce qui est indexé. L'élève recevait donc une invitation à
travailler un chapitre que l'agent allait refuser au tour suivant — refus
correct, invitation fautive.

Cette route supprime la seconde source de vérité plutôt que de la resynchroniser
à la main : le catalogue est lu dans le store vectoriel, exactement comme le
font déjà les tours méta et l'accueil de l'agent (``retriever.catalogue``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from agent_tuteur.api.dependencies import get_current_user, get_retriever
from agent_tuteur.api.schemas import CatalogueOut
from agent_tuteur.api.security import Principal
from agent_tuteur.vectorstore.retriever import HybridRetriever

router = APIRouter(prefix="/api/catalogue", tags=["catalogue"])


@router.get("", response_model=CatalogueOut)
async def get_catalogue(
    serie: str | None = Query(default=None),
    niveau: str | None = Query(default=None),
    classe: str | None = Query(default=None),
    discipline: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    retriever: HybridRetriever = Depends(get_retriever),
) -> CatalogueOut:
    """Chapitres disponibles pour ce cadre curriculaire (vide si rien n'est indexé).

    Les filtres reprennent ceux de la recherche : un élève de S2 ne doit pas se
    voir proposer un chapitre réservé à une autre série. Une liste vide est une
    réponse légitime — c'est au client de le dire honnêtement, pas d'inventer.
    """
    contexte = {
        cle: valeur
        for cle, valeur in {
            "serie": serie,
            "niveau": niveau,
            "classe": classe,
            "discipline": discipline,
        }.items()
        if valeur
    }
    return CatalogueOut(chapitres=retriever.catalogue(contexte))
