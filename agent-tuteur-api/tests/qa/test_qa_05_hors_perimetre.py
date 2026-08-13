"""Cas QA #5 — chunks non pertinents servis faute de seuil (Pierre Ndong).

« Quelle est la différence entre une suite arithmétique et une suite
géométrique ? » — les suites ne sont pas dans l'index figé de la démo. Le
système remontait quand même des extraits « Nombres Complexes » et « Calcul
Intégral » aux scores 0,55 / 0,45 / 0,40. Le testeur l'a relevé comme la preuve
directe d'un problème de seuil de pertinence.

Tout ce module est marqué ``bge`` : le seuil est une propriété de l'espace
vectoriel, et « light » n'en admet aucun (mesuré sur les 12 leçons, les
questions couvertes et les questions étrangères s'y recouvrent — 0,278 contre
0,524). Juger ce cas sur « light » ferait passer pour vert un correctif
inopérant. Il se juge donc sur BGE-M3, embedder de production depuis D3.

Le repli suit la décision **D6** : divulguer *puis* aider. L'agent dit qu'il n'a
pas ce chapitre et répond quand même — refuser tout net dégraderait les fixtures
positives #54 et #55, qui portent sur des dérivées, absentes de l'index, et dont
le comportement validé est une réponse correcte.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.prompt import CONSIGNE_HORS_PERIMETRE

from .cas import cas_critiques, cas_positifs, par_id

pytestmark = pytest.mark.bge

CAS = par_id(cas_critiques())
POSITIFS = par_id(cas_positifs())


def _sans_seuil_declare() -> bool:
    """Lu sur la classe : instancier BGE-M3 pour l'apprendre coûterait 8 minutes."""
    from agent_tuteur.vectorstore.embeddings import BGEM3Embedder

    return BGEM3Embedder.seuil_pertinence is None


@pytest.fixture(autouse=True)
def _exige_un_seuil():
    """Sans seuil déclaré, ce module n'a rien à juger — et le dit.

    La mécanique de seuil est en place et couverte par
    ``tests/test_seuil_pertinence.py``. Reste à trancher **la grandeur** à
    seuiller : mesuré sur le corpus figé, le cosinus dense ne sépare pas
    (le prompt exact du cas #5 vaut 0,5031 quand la question couverte la plus
    faible vaut 0,5178 — 0,015 d'écart, soit un ajustement au prompt du
    testeur), tandis que le score lexical de BGE-M3 sépare (0,1402 contre
    0,2105). Cf. `qa/qa_status.json` #5.

    Ces tests s'activeront d'eux-mêmes le jour où un embedder déclarera un
    seuil : ils ne sont pas suspendus, ils attendent leur grandeur.
    """
    if _sans_seuil_declare():
        pytest.skip("aucun seuil de pertinence déclaré : grandeur à seuiller non tranchée")

#: Ce que le corpus figé de la démo contient réellement.
CHAPITRES_INDEXES = {"Les Nombres Complexes", "Le Calcul Intégral"}


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_ne_sert_aucun_extrait(agent_qa_bge, session_eleve):
    """Règle non-négociable n°4, dans sa lettre : aucun chunk sous le seuil."""
    resultat = await agent_qa_bge.respond(CAS[5].prompt, {"serie": "S2"}, session_eleve)

    assert resultat.retrieved == [], (
        "extraits servis sur les suites, absentes de l'index : "
        f"{[sc.chunk.metadata.chapitre for sc in resultat.retrieved]}"
    )
    assert resultat.trace["hors_perimetre"] is True
    assert resultat.trace["sources"] == []


async def test_le_prompt_exact_avoue_le_hors_perimetre_sans_refuser(agent_qa_bge):
    """Décision D6 : l'aveu part au modèle, et l'aide n'est pas coupée.

    Le tour n'est pas court-circuité — pas de ``reponse_directe``, contrairement
    à la branche de sécurité du cas #7. L'élève reçoit une réponse ; il apprend
    seulement qu'elle ne vient pas de son programme.
    """
    prepared = await agent_qa_bge.prepare(CAS[5].prompt, {"serie": "S2"}, SessionState())

    assert CONSIGNE_HORS_PERIMETRE in prepared.final_prompt
    assert prepared.reponse_directe is None


# --- La cause racine, pas la formulation du testeur ---------------------------


@pytest.mark.parametrize(
    "question",
    [
        # Des mathématiques de terminale, mais absentes des deux chapitres
        # indexés — le cas qui compte : c'est du vocabulaire proche.
        "comment calculer la médiane d'une série statistique ?",
        "c'est quoi une loi binomiale",
        "résoudre l'équation différentielle y' = 2y",
        "comment montrer qu'une suite est majorée ?",
        # Hors mathématiques franc.
        "explique-moi la Seconde Guerre mondiale",
    ],
)
async def test_les_questions_hors_perimetre_ne_servent_aucun_extrait(question, agent_qa_bge):
    """Un correctif qui ne vaudrait que pour la phrase de Pierre Ndong ne vaut rien.

    Ces formulations ne figurent dans aucun backlog : elles vérifient que c'est
    bien le seuil qui agit, et non un filtrage taillé sur le prompt du cas.
    """
    resultat = await agent_qa_bge.respond(question, {"serie": "S2"}, SessionState())

    assert resultat.retrieved == [], (
        f"« {question} » a servi "
        f"{[sc.chunk.metadata.chapitre for sc in resultat.retrieved]}"
    )
    assert resultat.trace["hors_perimetre"] is True


# --- Non-régression : le seuil ne doit pas fermer le corpus -------------------


@pytest.mark.parametrize(
    "question",
    [
        "c'est quoi le conjugué d'un nombre complexe ?",
        "comment calculer le module de z ?",
        "comment calculer une primitive ?",
        "explique-moi l'intégration par parties",
    ],
)
async def test_les_questions_couvertes_sont_toujours_servies(question, agent_qa_bge):
    """Le risque exact du correctif : un seuil trop haut ferme le corpus.

    C'est le défaut du cas #6 en sens inverse — un chapitre pourtant indexé
    devenu inatteignable. Ces quatre questions portent sur les deux chapitres
    réellement présents et doivent continuer à recevoir du cours.
    """
    resultat = await agent_qa_bge.respond(question, {"serie": "S2"}, SessionState())

    assert resultat.retrieved, f"« {question} » ne reçoit plus aucun extrait"
    assert resultat.trace["hors_perimetre"] is False
    assert {sc.chunk.metadata.chapitre for sc in resultat.retrieved} <= CHAPITRES_INDEXES


async def test_le_cas_06_reste_servi_par_son_chapitre(agent_qa_bge, session_eleve):
    """Fixture croisée : le cas #6 a été clos sur ce même corpus.

    Il exige l'inverse du cas #5 — des extraits « Nombres Complexes » bien
    servis. Un seuil mal placé le rouvrirait sans que son propre test, qui
    tourne sur « light », ne s'en aperçoive.
    """
    resultat = await agent_qa_bge.respond(CAS[6].prompt, {"serie": "S2"}, session_eleve)

    assert {sc.chunk.metadata.chapitre for sc in resultat.retrieved} == {
        "Les Nombres Complexes"
    }


# --- Non-régression : les fixtures positives #54 et #55 ----------------------


@pytest.mark.parametrize("cid", [54, 55])
async def test_les_derivees_ne_sont_pas_refusees(cid, agent_qa_bge):
    """Décision D6, sa raison d'être.

    Les deux fixtures portent sur des dérivées, absentes des chapitres indexés :
    le seuil les fait donc tomber hors périmètre. Leur comportement confirmé est
    pourtant une réponse correcte — un repli qui refuserait de répondre les
    dégraderait, ce que CLAUDE.md interdit sans validation humaine.

    Le tour doit aller jusqu'au bout : aucun court-circuit (contrairement à la
    branche de sécurité), et la consigne de repli est celle qui divulgue *et*
    aide.
    """
    prepared = await agent_qa_bge.prepare(POSITIFS[cid].prompt, {"serie": "S2"}, SessionState())

    assert prepared.reponse_directe is None, "tour court-circuité : la fixture est dégradée"
    assert prepared.trace["hors_perimetre"] is True
    assert CONSIGNE_HORS_PERIMETRE in prepared.final_prompt


async def test_la_derivee_du_cas_55_reste_calculee_et_juste(agent_qa_bge, session_eleve):
    """La moitié vérifiable du #55 : le hors-périmètre ne coupe pas SymPy.

    « Calcule la dérivée de f(x) = x²·ln(x) » — le comportement validé par le
    testeur est un calcul correct. Il ne vient pas du corpus mais de l'outil
    symbolique, et c'est précisément pourquoi divulguer l'absence de cours ne
    force pas à se taire (règle n°2 : ce qui est annoncé est vérifié).
    """
    import sympy

    resultat = await agent_qa_bge.respond(POSITIFS[55].prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["tool_used"] == "sympy_calculator"
    calcule = resultat.trace["tool_result"].split("→")[-1].strip()
    attendu = sympy.sympify("2*x*log(x) + x")
    assert sympy.simplify(sympy.sympify(calcule) - attendu) == 0, calcule
    assert resultat.trace["calcul_non_verifie"] is False
