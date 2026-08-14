"""Cas QA #5 — chunks non pertinents servis faute de périmètre (Pierre Ndong).

« Quelle est la différence entre une suite arithmétique et une suite
géométrique ? » remontait des extraits « Nombres Complexes » et « Calcul
Intégral » aux scores 0,55 / 0,45 / 0,40. Le testeur l'a relevé comme la preuve
directe d'un problème de seuil de pertinence.

**Ce qui a été mesuré, et qui déplace le cas.** Les suites *sont* dans le corpus
(`Lecon_02` et `Lecon_10`). Le défaut observé en démo venait d'un **index
incomplet** — trois leçons sur douze n'avaient jamais été ingérées. Sur le
corpus complet, ce prompt reçoit « Les Suites Numériques », comme il se doit.
Ce module le vérifie plutôt que de figer le symptôme.

**La règle de périmètre n'est pas un seuil.** Remesuré sur les 12 leçons (216
chunks, 35 questions couvertes contre 18 étrangères), aucun score scalaire ne
sépare les deux nuages : marge −0,127 sur le cosinus dense, −0,024 sur le poids
lexical. Ce qui sépare est le **consensus de chapitre** du top-k — une question
couverte concentre ses résultats, une question étrangère les éparpille faute de
foyer dans le corpus. À 0,8 sous BGE-M3 : 5,7 % de faux rejets, 16,7 % de faux
services.

**Pourquoi ce module s'indexe sur les 12 leçons et non sur le corpus figé QA.**
Le pouvoir discriminant du consensus dépend de la *largeur* du corpus, et cela a
été mesuré : sur le corpus figé à 2 chapitres, le même réglage donne **66,7 %
de faux services** — avec deux chapitres seulement, le top-k de n'importe quelle
question se concentre par construction, y compris celui de « c'est quoi la
photosynthèse ». Juger le correctif là-dessus le déclarerait cassé alors que
c'est le corpus qui est trop étroit. Corollaire d'exploitation, qui ne doit pas
se perdre : **la démo doit tourner sur l'index complet** pour que cette règle
fonctionne.

Le repli suit la décision **D6** : divulguer *puis* aider. L'agent dit qu'il n'a
pas ce chapitre et répond quand même — refuser tout net dégraderait les fixtures
positives #54 et #55, qui portent sur des dérivées, absentes de l'index, et dont
le comportement validé est une réponse correcte.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.llm.mock import MockLLM
from agent_tuteur.agent.ports import InMemoryAuditLog, InMemoryStudentMemory
from agent_tuteur.agent.prompt import CONSIGNE_HORS_PERIMETRE
from agent_tuteur.ingestion.pipeline import ingest_and_index
from agent_tuteur.vectorstore.embeddings import build_embedder
from agent_tuteur.vectorstore.indexer import Indexer
from agent_tuteur.vectorstore.retriever import HybridRetriever
from agent_tuteur.vectorstore.store import build_vector_store

from .cas import cas_critiques, cas_positifs, par_id

pytestmark = pytest.mark.bge

CAS = par_id(cas_critiques())
POSITIFS = par_id(cas_positifs())

#: Le corpus de production, pas l'extrait figé — cf. l'en-tête du module.
CORPUS_COMPLET = Path(__file__).resolve().parents[3] / "lessons"

CONTEXTE = {"serie": "S2"}


@pytest.fixture(autouse=True)
def _exige_une_regle_de_perimetre():
    """La grandeur à seuiller a été tranchée — et ce n'est pas un score.

    Ces tests s'activeront d'eux-mêmes si un jour un embedder cesse d'en
    déclarer une : ils ne sont pas suspendus, ils jugent une règle existante.
    """
    from agent_tuteur.vectorstore.embeddings import BGEM3Embedder

    if BGEM3Embedder.consensus_chapitre is None:
        pytest.skip("aucune règle de périmètre déclarée par l'embedder de production")


@pytest.fixture(scope="session")
def agent_corpus_complet():
    """Les 12 leçons encodées par l'embedder de production.

    Portée « session » : l'encodage des 216 chunks prend une trentaine de
    minutes sur CPU. C'est le prix d'un verdict qui porte sur la pile réelle
    plutôt que sur une maquette — et le module est opt-in (``QA_BGE=1``).
    """
    try:
        import FlagEmbedding  # type: ignore  # noqa: F401
    except ImportError:
        pytest.skip("FlagEmbedding non installé")
    embedder = build_embedder("bge_m3")
    store = build_vector_store("memory", rrf_k=60)
    indexer = Indexer(embedder, store)
    for chemin in sorted(CORPUS_COMPLET.glob("*.md")):
        ingest_and_index(chemin.name, chemin.read_bytes(), indexer)
    retriever = HybridRetriever(embedder, store, top_k=5)
    return TutorAgent(
        retriever, MockLLM(),
        memory=InMemoryStudentMemory(), audit=InMemoryAuditLog(), top_k=5,
    )


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_recoit_son_vrai_chapitre(agent_corpus_complet, session_eleve):
    """Ce que le testeur aurait dû voir : les suites, sur une question de suites.

    Le symptôme rapporté — des extraits « Nombres Complexes » et « Calcul
    Intégral » — venait de l'index incomplet, pas du code de recherche. Un
    correctif qui se contenterait de ne plus rien servir sur ce prompt
    satisferait la lettre du ticket en aggravant le produit.
    """
    resultat = await agent_corpus_complet.respond(CAS[5].prompt, CONTEXTE, session_eleve)

    assert {sc.chunk.metadata.chapitre for sc in resultat.retrieved} == {
        "Les Suites Numériques"
    }
    assert resultat.trace["hors_perimetre"] is False


# --- La cause racine : ce que le corpus ne couvre pas -------------------------


@pytest.mark.parametrize(
    "question",
    [
        # Des mathématiques de terminale, absentes des chapitres servis en S2 —
        # le cas qui compte, parce que le vocabulaire est proche.
        "c'est quoi la dérivée d'une fonction composée",
        "c'est quoi une asymptote oblique",
        "c'est quoi un produit scalaire dans l'espace",
        # Hors mathématiques franc.
        "explique-moi la Seconde Guerre mondiale",
        "c'est quoi la photosynthèse",
        "comment conjuguer le verbe aller au subjonctif",
    ],
)
async def test_les_questions_hors_perimetre_ne_servent_aucun_extrait(
    question, agent_corpus_complet
):
    """Un correctif qui ne vaudrait que pour la phrase de Pierre Ndong ne vaut rien.

    Ces formulations ne figurent dans aucun backlog : elles vérifient que c'est
    bien la règle qui agit, et non un filtrage taillé sur le prompt du cas.
    """
    resultat = await agent_corpus_complet.respond(question, CONTEXTE, SessionState())

    assert resultat.retrieved == [], (
        f"« {question} » a servi "
        f"{[sc.chunk.metadata.chapitre for sc in resultat.retrieved]}"
    )
    assert resultat.trace["hors_perimetre"] is True


@pytest.mark.parametrize(
    "question",
    [
        "explique-moi la limite de sin(x)/x en 0",
        "comment calculer le volume d'une pyramide",
        "comment résoudre une inéquation du second degré",
    ],
)
async def test_les_faux_services_connus_restent_connus(question, agent_corpus_complet):
    """Les 16,7 % de faux services, nommés plutôt que passés sous silence.

    Ces trois questions franchissent le consensus : leur vocabulaire est
    suffisamment proche d'un chapitre réel (intégrales, suites, équations) pour
    que le top-k s'y concentre. C'est la moitié perdante du compromis mesuré, et
    la décision D6 la rend supportable — l'élève reçoit une réponse, jamais un
    cours présenté comme le sien à tort.

    Ce test échouera si le taux s'améliore. C'est voulu : il faudra alors
    remesurer et remonter la borne, pas découvrir l'écart en production.
    """
    resultat = await agent_corpus_complet.respond(question, CONTEXTE, SessionState())

    assert resultat.retrieved, (
        f"« {question} » n'est plus servie : le compromis a changé, "
        "remesurer le consensus avant de mettre à jour ce test"
    )


# --- Non-régression : la règle ne doit pas fermer le corpus -------------------


@pytest.mark.parametrize(
    "question",
    [
        "c'est quoi le conjugué d'un nombre complexe ?",
        "comment calculer le module de z ?",
        "comment calculer une primitive ?",
        "explique-moi l'intégration par parties",
        "comment montrer qu'une suite est majorée ?",
        "résoudre l'équation différentielle y' = 2y",
        "c'est quoi une loi binomiale",
        "comment calculer une probabilité conditionnelle",
    ],
)
async def test_les_questions_couvertes_sont_toujours_servies(question, agent_corpus_complet):
    """Le risque exact du correctif : un périmètre trop serré ferme le corpus.

    C'est le défaut du cas #6 en sens inverse — un chapitre pourtant indexé
    devenu inatteignable. Ces huit questions couvrent six chapitres réellement
    présents et doivent continuer à recevoir du cours.
    """
    resultat = await agent_corpus_complet.respond(question, CONTEXTE, SessionState())

    assert resultat.retrieved, f"« {question} » ne reçoit plus aucun extrait"
    assert resultat.trace["hors_perimetre"] is False
    # Le consensus ne sert qu'un chapitre : c'est ce qui fait sa valeur.
    assert len({sc.chunk.metadata.chapitre for sc in resultat.retrieved}) == 1


async def test_le_cas_06_reste_servi_par_son_chapitre(agent_corpus_complet, session_eleve):
    """Fixture croisée : le cas #6 a été clos sur ce même sujet.

    Il exige l'inverse du cas #5 — des extraits « Nombres Complexes » bien
    servis. Une règle de périmètre mal réglée le rouvrirait sans que son propre
    test, qui tourne sur « light », ne s'en aperçoive.
    """
    resultat = await agent_corpus_complet.respond(CAS[6].prompt, CONTEXTE, session_eleve)

    assert {sc.chunk.metadata.chapitre for sc in resultat.retrieved} == {
        "Les Nombres Complexes"
    }


# --- Non-régression : les fixtures positives #54 et #55 ----------------------


@pytest.mark.parametrize("cid", [54, 55])
async def test_les_derivees_ne_sont_pas_refusees(cid, agent_corpus_complet):
    """Décision D6, sa raison d'être.

    Les deux fixtures portent sur des dérivées, absentes des chapitres indexés :
    la règle les fait donc tomber hors périmètre. Leur comportement confirmé est
    pourtant une réponse correcte — un repli qui refuserait de répondre les
    dégraderait, ce que CLAUDE.md interdit sans validation humaine.

    Le tour doit aller jusqu'au bout : aucun court-circuit (contrairement à la
    branche de sécurité), et la consigne de repli est celle qui divulgue *et*
    aide.
    """
    prepared = await agent_corpus_complet.prepare(
        POSITIFS[cid].prompt, CONTEXTE, SessionState()
    )

    assert prepared.reponse_directe is None, "tour court-circuité : la fixture est dégradée"
    assert prepared.trace["hors_perimetre"] is True
    assert CONSIGNE_HORS_PERIMETRE in prepared.final_prompt


async def test_la_derivee_du_cas_55_reste_calculee_et_juste(
    agent_corpus_complet, session_eleve
):
    """La moitié vérifiable du #55 : le hors-périmètre ne coupe pas SymPy.

    « Calcule la dérivée de f(x) = x²·ln(x) » — le comportement validé par le
    testeur est un calcul correct. Il ne vient pas du corpus mais de l'outil
    symbolique, et c'est précisément pourquoi divulguer l'absence de cours ne
    force pas à se taire (règle n°2 : ce qui est annoncé est vérifié).
    """
    import sympy

    resultat = await agent_corpus_complet.respond(
        POSITIFS[55].prompt, CONTEXTE, session_eleve
    )

    assert resultat.trace["tool_used"] == "sympy_calculator"
    calcule = resultat.trace["tool_result"].split("→")[-1].strip()
    attendu = sympy.sympify("2*x*log(x) + x")
    assert sympy.simplify(sympy.sympify(calcule) - attendu) == 0, calcule
    assert resultat.trace["calcul_non_verifie"] is False
