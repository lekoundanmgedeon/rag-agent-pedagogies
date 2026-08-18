"""Seuil de pertinence du retrieval — le mécanisme, à valeur imposée.

Cas QA #5 : une question sur les suites (absentes de l'index) remontait des
extraits « Nombres Complexes » et « Calcul Intégral ». Règle non-négociable
n°4 : sous un seuil minimal, aucun chunk ne doit être utilisé.

Ce module ne juge **aucune valeur calibrée** : il fixe le seuil de force et
vérifie la mécanique — ce qui est écarté, ce qui est conservé, et où le filtre
ne doit surtout pas s'appliquer. La valeur réelle dépend de l'embedder et se
mesure sur le vrai modèle (cf. ``tests/qa/test_qa_05_hors_perimetre.py``).
"""

from __future__ import annotations

from agent_tuteur.config.taxonomy import taxonomy_key
from agent_tuteur.domain.models import Chunk, CurriculumMetadata, ScoredChunk
from agent_tuteur.vectorstore.embeddings import BaseEmbedder, LightEmbedder
from agent_tuteur.vectorstore.retriever import HybridRetriever


class _Embedder(BaseEmbedder):
    """Embedder muet : ici seuls ses *réglages déclarés* comptent."""

    def __init__(self, seuil: float | None, consensus: float | None = None) -> None:
        self.seuil_pertinence = seuil
        self.consensus_chapitre = consensus

    @property
    def dense_dim(self) -> int:
        return 4

    def embed_documents(self, texts):
        raise NotImplementedError

    def embed_query(self, text):
        return None


class _Store:
    """Store factice : rend les ``ScoredChunk`` qu'on lui a donnés, en ordre."""

    def __init__(self, resultats: list[ScoredChunk]) -> None:
        self.resultats = resultats
        self.derniers_filtres: dict | None = None

    def search(self, query, top_k=5, filters=None):
        self.derniers_filtres = filters
        return self.resultats[:top_k]

    def catalogue(self, filters=None):
        return []


def _sc(identifiant: str, dense: float | None, chapitre: str = "Les Nombres Complexes"):
    return ScoredChunk(
        chunk=Chunk(
            id=identifiant,
            text=f"texte {identifiant}",
            metadata=CurriculumMetadata(niveau="secondaire", chapitre=chapitre),
        ),
        score=0.03,          # RRF : volontairement identique partout, il ne sert à rien ici
        dense_score=dense,
    )


def _retriever(resultats, *, seuil_embedder=0.40, seuil_explicite=None):
    store = _Store(resultats)
    return HybridRetriever(
        _Embedder(seuil_embedder), store, top_k=10, seuil_pertinence=seuil_explicite
    ), store


# --- Ce que le seuil écarte ---------------------------------------------------


def test_les_extraits_sous_le_seuil_sont_ecartes():
    """Le défaut du cas #5 : les moins mauvais résultats d'un corpus étranger."""
    retriever, _ = _retriever([_sc("a", 0.81), _sc("b", 0.55), _sc("c", 0.39), _sc("d", 0.12)])

    resultats = retriever.retrieve("différence entre suite arithmétique et géométrique")

    assert [sc.chunk.id for sc in resultats] == ["a", "b"]


def test_aucun_extrait_ne_survit_a_une_question_hors_sujet():
    """Le cas limite qui compte : la liste vide, pas « le meilleur des mauvais ».

    C'est cette liste vide que le graphe traduit en ``hors_perimetre``, puis le
    prompt en aveu honnête à l'élève.
    """
    retriever, _ = _retriever([_sc("a", 0.31), _sc("b", 0.22), _sc("c", 0.05)])

    assert retriever.retrieve("qui a gagné la coupe du monde 2018") == []


def test_la_valeur_exactement_egale_au_seuil_est_conservee():
    """Frontière fermée : le seuil est un minimum acceptable, pas un exclu."""
    retriever, _ = _retriever([_sc("a", 0.40)])

    assert [sc.chunk.id for sc in retriever.retrieve("q")] == ["a"]


# --- Ce que le seuil ne doit PAS écarter --------------------------------------


def test_un_cosinus_inconnu_est_conserve():
    """``None`` veut dire « pas mesuré », pas « orthogonal ».

    Qdrant peut ne pas renvoyer un point dans la requête dense de rappel des
    cosinus. Rejeter sur une absence de mesure écarterait du cours pertinent —
    c'est le défaut du cas QA #6, en sens inverse.
    """
    retriever, _ = _retriever([_sc("a", None), _sc("b", 0.10)])

    assert [sc.chunk.id for sc in retriever.retrieve("q")] == ["a"]


def test_sans_seuil_declare_rien_n_est_filtre():
    """``LightEmbedder`` n'expose aucun seuil : mesuré, il n'en existe pas.

    Un seuil inventé pour cet espace vectoriel serait pire que pas de seuil :
    il écarterait du cours pertinent en silence.
    """
    retriever, _ = _retriever([_sc("a", 0.31), _sc("b", 0.02)], seuil_embedder=None)

    assert len(retriever.retrieve("q")) == 2
    assert LightEmbedder().seuil_pertinence is None


def test_une_recherche_deja_circonscrite_au_chapitre_ignore_le_seuil():
    """Mode cours : l'appartenance est établie par les métadonnées.

    ``chunks_du_chapitre`` ne se sert de la similarité que pour ordonner un
    ensemble déjà filtré. Y appliquer le seuil rendrait « 7. Méthodes »
    inatteignable depuis « fais-moi un cours sur les nombres complexes » — soit
    la régression exacte du cas QA #12.
    """
    retriever, store = _retriever([_sc("a", 0.81), _sc("b", 0.12), _sc("c", None)])

    resultats = retriever.chunks_du_chapitre("Les Nombres Complexes", {"serie": "S2"})

    assert [sc.chunk.id for sc in resultats] == ["a", "b", "c"]
    assert store.derniers_filtres["chapitre"] == [taxonomy_key("Les Nombres Complexes")]


# --- D'où vient la valeur -----------------------------------------------------


def test_le_seuil_vient_de_l_embedder_par_defaut():
    """Le seuil est une propriété de l'espace vectoriel, pas de l'application.

    La même valeur n'a aucun sens d'un backend à l'autre : un seuil hérité d'un
    embedder précédent écarterait du cours pertinent sans rien signaler.
    """
    retriever, _ = _retriever([], seuil_embedder=0.47)

    assert retriever.seuil_pertinence == 0.47


def test_le_reglage_explicite_prime_sur_l_embedder():
    """Ajustement en exploitation sans redéploiement (``RAG_SEUIL_PERTINENCE``)."""
    retriever, _ = _retriever([_sc("a", 0.50)], seuil_embedder=0.40, seuil_explicite=0.60)

    assert retriever.seuil_pertinence == 0.60
    assert retriever.retrieve("q") == []


# =============================================================================
# Consensus de chapitre — la règle de périmètre proprement dite (cas QA #5)
# =============================================================================
# Mesuré sur les 12 leçons avec BGE-M3, aucun score scalaire ne sépare les
# questions couvertes des questions étrangères : toutes les marges sont
# négatives. Ce qui sépare est l'accord des résultats — une question couverte
# concentre son top-k sur un chapitre, une question étrangère l'éparpille.
# Comme au-dessus, ce module ne juge aucune valeur calibrée : il impose la
# fraction et vérifie la mécanique.

COMPLEXES = "Les Nombres Complexes"
INTEGRALES = "Le Calcul Intégral"
SUITES = "Les Suites Numériques"


def _retriever_consensus(resultats, *, consensus=0.8, explicite=None, top_k=10):
    store = _Store(resultats)
    return HybridRetriever(
        _Embedder(None, consensus), store, top_k=top_k, consensus_chapitre=explicite
    ), store


def test_un_top_k_eparpille_ne_sert_aucun_extrait():
    """Le prompt du cas #5, dans sa forme mesurée : trois chapitres, aucun foyer.

    « Quelle est la différence entre une suite arithmétique et une suite
    géométrique ? » sur un corpus où les suites ne sont pas indexées : les
    résultats se répartissent faute de chapitre qui traite le sujet. Aucun
    extrait ne doit être servi (règle non-négociable n°4).
    """
    retriever, _ = _retriever_consensus([
        _sc("a", 0.55, COMPLEXES), _sc("b", 0.52, INTEGRALES), _sc("c", 0.51, SUITES),
        _sc("d", 0.50, COMPLEXES), _sc("e", 0.48, INTEGRALES),
    ])

    assert retriever.retrieve("différence entre suite arithmétique et géométrique") == []


def test_un_chapitre_majoritaire_est_servi_seul():
    """Une question couverte : le chapitre qui fait consensus, et lui seul."""
    retriever, _ = _retriever_consensus([
        _sc("a", 0.61, COMPLEXES), _sc("b", 0.60, COMPLEXES), _sc("c", 0.58, COMPLEXES),
        _sc("d", 0.57, COMPLEXES), _sc("e", 0.40, INTEGRALES),
    ])

    assert [sc.chunk.id for sc in retriever.retrieve("le conjugué de z")] == \
        ["a", "b", "c", "d"]


def test_la_fraction_exacte_suffit():
    """Frontière fermée : 4 sur 5 à 0,8, c'est le réglage mesuré lui-même."""
    retriever, _ = _retriever_consensus([
        _sc("a", 0.6, COMPLEXES), _sc("b", 0.6, COMPLEXES),
        _sc("c", 0.6, COMPLEXES), _sc("d", 0.6, COMPLEXES), _sc("e", 0.6, SUITES),
    ])

    assert len(retriever.retrieve("q")) == 4


def test_un_extrait_de_moins_fait_basculer_hors_perimetre():
    """Le pendant du précédent : 3 sur 5 ne fait pas un périmètre."""
    retriever, _ = _retriever_consensus([
        _sc("a", 0.6, COMPLEXES), _sc("b", 0.6, COMPLEXES), _sc("c", 0.6, COMPLEXES),
        _sc("d", 0.6, SUITES), _sc("e", 0.6, INTEGRALES),
    ])

    assert retriever.retrieve("q") == []


def test_le_vote_se_lit_sur_une_fenetre_fixe_pas_sur_tout_le_vivier():
    """Le piège de ``retrieve_course_first``, qui ratisse quatre fois plus large.

    Vingt résultats dont les cinq meilleurs font consensus : appliquer la
    fraction au vivier entier exigerait seize extraits du même chapitre — une
    règle bien plus sévère que celle qui a été mesurée, et qui rejetterait des
    questions pleinement couvertes sans que rien ne le signale.
    """
    resultats = [_sc(f"tete{i}", 0.6, COMPLEXES) for i in range(4)]
    resultats.append(_sc("tete4", 0.6, INTEGRALES))
    resultats += [_sc(f"queue{i}", 0.3, INTEGRALES) for i in range(15)]

    retriever, _ = _retriever_consensus(resultats, top_k=20)

    servis = retriever.retrieve("le conjugué de z")
    assert [sc.chunk.id for sc in servis] == ["tete0", "tete1", "tete2", "tete3"]


def test_sans_consensus_declare_rien_n_est_filtre():
    """``LightEmbedder`` n'en déclare aucun : mesuré, la règle n'y tient pas.

    Le vote de chapitre suppose une proximité de sens. Sur un hachage de
    n-grammes, il donne 40 % de faux rejets — deux questions couvertes sur cinq
    déclarées hors programme. L'activer là serait pire que ne rien filtrer.
    """
    retriever, _ = _retriever_consensus([
        _sc("a", 0.5, COMPLEXES), _sc("b", 0.5, INTEGRALES), _sc("c", 0.5, SUITES),
    ], consensus=None)

    assert len(retriever.retrieve("q")) == 3
    assert LightEmbedder().consensus_chapitre is None


def test_une_recherche_deja_circonscrite_ignore_le_consensus():
    """Mode cours : l'appartenance est établie par les métadonnées (cas QA #12).

    ``chunks_du_chapitre`` filtre déjà sur le chapitre ; le vote n'a rien à y
    décider, et une section au titre éloigné doit rester atteignable.
    """
    retriever, _ = _retriever_consensus([
        _sc("a", 0.6, COMPLEXES), _sc("b", 0.6, INTEGRALES), _sc("c", 0.6, SUITES),
    ])

    resultats = retriever.chunks_du_chapitre(COMPLEXES, {"serie": "S2"})

    assert [sc.chunk.id for sc in resultats] == ["a", "b", "c"]


def test_des_extraits_sans_chapitre_ne_ferment_pas_le_corpus():
    """Un chunk sans chapitre est muet, pas contradictoire.

    Aucun vote exprimé : on ne peut rien conclure, donc on ne retranche rien —
    plutôt que de traduire une métadonnée manquante en « hors programme ».
    """
    retriever, _ = _retriever_consensus([
        _sc("a", 0.6, None), _sc("b", 0.6, None), _sc("c", 0.6, None),
    ])

    assert len(retriever.retrieve("q")) == 3


def test_le_consensus_vient_de_l_embedder_par_defaut():
    """Comme le seuil : c'est la qualité sémantique du backend qui le porte."""
    retriever, _ = _retriever_consensus([], consensus=0.8)

    assert retriever.consensus_chapitre == 0.8


def test_le_reglage_explicite_prime_sur_l_embedder_pour_le_consensus():
    """Resserrage en exploitation sans redéploiement (``RAG_CONSENSUS_CHAPITRE``)."""
    retriever, _ = _retriever_consensus([
        _sc("a", 0.6, COMPLEXES), _sc("b", 0.6, COMPLEXES),
        _sc("c", 0.6, COMPLEXES), _sc("d", 0.6, COMPLEXES), _sc("e", 0.6, SUITES),
    ], consensus=0.8, explicite=1.0)

    assert retriever.consensus_chapitre == 1.0
    assert retriever.retrieve("q") == []  # l'unanimité était à un extrait près


def test_l_embedder_de_production_declare_le_consensus_mesure():
    """Lu sur la classe : instancier BGE-M3 pour l'apprendre coûterait 8 minutes."""
    from agent_tuteur.vectorstore.embeddings import BGEM3Embedder

    assert BGEM3Embedder.consensus_chapitre == 0.8
