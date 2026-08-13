"""Retriever hybride filtré par métadonnées curriculaires.

Rôle : traduire un *contexte curriculaire* (niveau, série, discipline…) en
filtres de store, encoder la question au même format que le contenu, et renvoyer
les chunks les plus pertinents avec leurs scores. L'expansion des alias de série
est appliquée ici pour qu'une question en « STIDD1 » atteigne des chunks « T1 ».
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agent_tuteur.config.taxonomy import (
    CHAMPS_INDEXES,
    CHAMPS_NORMALISES,
    serie_aliases,
    taxonomy_key,
)
from agent_tuteur.domain.models import ScoredChunk
from agent_tuteur.vectorstore.embeddings import BaseEmbedder
from agent_tuteur.vectorstore.store import BaseVectorStore, Filters

logger = logging.getLogger(__name__)

#: Nombre de compléments (TD, exercices) joints par défaut à une réponse de
#: cours : de quoi illustrer, pas de quoi noyer le cours lui-même.
QUOTA_COMPLEMENTS_PAR_DEFAUT = 2

#: Facteur de sur-échantillonnage avant partition. Il faut ratisser plus large
#: que ``top_k`` pour qu'il reste des chunks de cours **et** des compléments
#: après séparation : sur ce corpus, les premiers résultats sont souvent tous
#: des exercices.
FACTEUR_SUR_ECHANTILLONNAGE = 4


def build_filters(context: dict) -> Filters:
    """Construit des filtres de store à partir d'un contexte curriculaire.

    Ne retient que les champs indexés non vides. Deux normalisations s'appliquent
    pour qu'un libellé saisi par un humain atteigne les chunks correspondants :

    * la **série** est étendue à tous ses alias équivalents (ancienne ↔ nouvelle
      nomenclature) — « STIDD1 » atteint des chunks « T1 » ;
    * les autres libellés curriculaires sont réduits à leur clé normalisée —
      « Mathematiques » atteint « Mathématiques », « Les Suites Numériques »
      atteint « Suites Numeriques ».

    Les valeurs renvoyées pour ces champs sont donc des *clés*, que les stores
    confrontent aux compagnons ``<champ>_key`` des chunks, jamais aux libellés.
    """
    filters: Filters = {}
    for field in CHAMPS_INDEXES:
        value = context.get(field)
        if not value:
            continue
        if field == "serie":
            filters[field] = serie_aliases(value)
            continue
        values = (
            [str(v) for v in value]
            if isinstance(value, (list, tuple, set))
            else [str(value)]
        )
        filters[field] = (
            [taxonomy_key(v) for v in values] if field in CHAMPS_NORMALISES else values
        )
    return filters


@dataclass(frozen=True)
class ResultatsPedagogiques:
    """Résultats de recherche séparés selon leur nature pédagogique.

    ``cours`` contient le cours proprement dit, ``complements`` les TD,
    exercices et annales qui l'illustrent. ``a_du_cours`` dit si le corpus a
    effectivement fourni du cours — c'est cette information qui permet à l'agent
    d'avouer qu'il n'en a pas, au lieu d'en inventer.
    """

    cours: list[ScoredChunk]
    complements: list[ScoredChunk]

    @property
    def a_du_cours(self) -> bool:
        return bool(self.cours)

    def tous(self) -> list[ScoredChunk]:
        """Tous les résultats, cours en tête."""
        return [*self.cours, *self.complements]


class HybridRetriever:
    def __init__(
        self,
        embedder: BaseEmbedder,
        store: BaseVectorStore,
        top_k: int = 5,
        seuil_pertinence: float | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._top_k = top_k
        #: ``None`` = celui de l'embedder, qui seul connaît son espace vectoriel.
        #: Le réglage n'existe que pour ajuster la valeur en exploitation sans
        #: redéployer ; il ne sert pas à en inventer une là où l'embedder dit
        #: qu'il n'y en a pas de posable.
        self._seuil = (
            embedder.seuil_pertinence if seuil_pertinence is None else seuil_pertinence
        )

    @property
    def seuil_pertinence(self) -> float | None:
        return self._seuil

    def _ecarter_les_hors_sujet(self, resultats: list[ScoredChunk]) -> list[ScoredChunk]:
        """Écarte les extraits dont le cosinus dense est sous le seuil.

        Règle non-négociable n°4 : sous un seuil minimal, **aucun** chunk n'est
        utilisé — mieux vaut un « je n'ai pas ça » honnête que les moins mauvais
        résultats d'un corpus qui ne traite pas le sujet. C'est le défaut
        démontré par le cas QA #5 : une question sur les suites remontait des
        extraits « Nombres Complexes » et « Calcul Intégral ».

        Le filtre porte sur ``dense_score`` (cosinus, borné et interprétable) et
        jamais sur ``score``, qui est un score de fusion RRF fondé sur les rangs
        : mesuré sur ce dépôt, un résultat hors périmètre y obtenait 0,0325
        contre 0,0323 pour un résultat couvert. Un seuil posé dessus classerait
        à l'envers.

        ``dense_score is None`` est **conservé**. Un point que Qdrant n'a pas
        renvoyé dans la requête dense est *inconnu*, pas orthogonal ; le rejeter
        écarterait du cours pertinent sur une absence de mesure — exactement le
        défaut du cas QA #6, en sens inverse.
        """
        if self._seuil is None:
            return resultats
        retenus = [
            sc for sc in resultats
            if sc.dense_score is None or sc.dense_score >= self._seuil
        ]
        if len(retenus) < len(resultats):
            mesures = [sc.dense_score for sc in resultats if sc.dense_score is not None]
            logger.info(
                "seuil de pertinence : %d/%d extraits écartés "
                "(meilleur cosinus %.4f, seuil %.2f)",
                len(resultats) - len(retenus), len(resultats),
                max(mesures, default=0.0), self._seuil,
            )
        return retenus

    def retrieve(
        self,
        query: str,
        context: dict | None = None,
        top_k: int | None = None,
        *,
        filtrer_par_pertinence: bool = True,
    ) -> list[ScoredChunk]:
        """Recherche ouverte, débarrassée des extraits hors sujet.

        ``filtrer_par_pertinence=False`` sert les recherches **déjà
        circonscrites par les métadonnées** (cf. :meth:`chunks_du_chapitre`),
        où la similarité ne sert qu'à ordonner un ensemble dont l'appartenance
        est établie par ailleurs.
        """
        filters = build_filters(context or {})
        query_emb = self._embedder.embed_query(query)
        resultats = self._store.search(
            query_emb, top_k=top_k or self._top_k, filters=filters
        )
        return self._ecarter_les_hors_sujet(resultats) if filtrer_par_pertinence else resultats

    def catalogue(self, context: dict | None = None) -> list[str]:
        """Chapitres réellement disponibles pour ce cadre curriculaire.

        Sert les tours **méta** (« quels chapitres as-tu ? »), qui ne doivent
        déclencher aucune recherche par similarité : la question porte sur la
        couverture du corpus, pas sur son contenu.
        """
        return self._store.catalogue(build_filters(context or {}))

    def chunks_du_chapitre(
        self, chapitre: str, context: dict | None = None, *, limite: int = 40
    ) -> list[ScoredChunk]:
        """Extraits d'un chapitre donné, ratissés large pour être triés ensuite.

        Le mode cours a besoin d'atteindre la section qu'il enseigne, pas la
        section la plus proche de la phrase de l'élève : « Fais-moi un cours sur
        les nombres complexes » ne ressemble lexicalement ni à « 3. Définitions »
        ni à « 7. Méthodes », si bien que la section servie tenait du hasard du
        classement (cas QA #12).

        On récupère donc largement **dans le chapitre** — le filtre porte sur les
        métadonnées, pas sur la similarité — et l'appelant choisit ensuite ses
        extraits sur le titre de section, de façon déterministe. La requête
        vectorielle ne sert plus qu'à ordonner un ensemble déjà circonscrit, ce
        qui rend le résultat indépendant du choix d'embedder resté ouvert (RC-0).

        Le seuil de pertinence ne s'applique donc **pas** ici : l'appartenance
        au chapitre est déjà établie par le filtre de métadonnées, et une
        section dont le titre ressemble peu à la phrase de l'élève (« 7.
        Méthodes ») doit rester atteignable.
        """
        cible = {**(context or {}), "chapitre": chapitre}
        return self.retrieve(chapitre, cible, top_k=limite, filtrer_par_pertinence=False)

    def retrieve_course_first(
        self,
        query: str,
        context: dict | None = None,
        *,
        top_k: int | None = None,
        quota_complements: int = QUOTA_COMPLEMENTS_PAR_DEFAUT,
    ) -> ResultatsPedagogiques:
        """Recherche à deux niveaux : le cours d'abord, les compléments sous quota.

        Utilisée quand l'élève demande une **explication** plutôt que de l'aide
        sur un exercice. Sans elle, une question comme « explique-moi les
        nombres complexes » remonte surtout des énoncés de TD, car ils sont
        majoritaires dans le corpus.

        Le classement produit par la fusion RRF est **conservé tel quel** : on
        ne fait que le partitionner puis le tronquer. Aucun calcul n'est fait
        sur les scores RRF, dont l'échelle (~1/(k+rang)) n'a pas de sens
        interprétable — les additionner ou les pondérer donnerait un résultat
        arbitraire.
        """
        k = top_k or self._top_k
        vivier = self.retrieve(query, context, top_k=k * FACTEUR_SUR_ECHANTILLONNAGE)

        cours = [sc for sc in vivier if sc.chunk.est_cours]
        complements = [sc for sc in vivier if not sc.chunk.est_cours]
        return ResultatsPedagogiques(
            cours=cours[:k],
            complements=complements[:quota_complements],
        )
