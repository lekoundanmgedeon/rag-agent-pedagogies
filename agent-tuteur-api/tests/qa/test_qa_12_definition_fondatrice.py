"""Cas QA #12 — « Fais-moi un cours sur les nombres complexes ».

Testeur : Tony SARRE. Observé : l'agent explique le contexte et l'utilité du
chapitre mais ne donne jamais la définition demandée (a+bi, i² = -1).

La classification initiale du backlog rangeait ce cas en résidu D2 — « les
chunks et le prompt portent déjà la section Définitions, seule la restitution
par le modèle manque ». La mesure a contredit ce diagnostic : au premier tour,
``trace['course']`` valait ``section_index=0, section_key='introduction'``, les
extraits injectés étaient Introduction / Astuces / Auto-évaluation, et ni
« a+ib » ni « i² = -1 » n'atteignaient le prompt. Le modèle ne pouvait pas
restituer une définition qu'il n'avait pas.

Deux causes racines, toutes deux structurelles :

* la consigne de la section « Introduction » disait littéralement « N'entre pas
  encore dans les définitions formelles » — le comportement rapporté était donc
  prescrit, pas accidentel ;
* la récupération a lieu **avant** ``course_planner`` et ne sait pas quelle
  section va être enseignée. La section servie tenait au hasard du classement
  par similarité, ce qui est d'autant moins fiable que l'embedder de la démo est
  un hachage sans sémantique (RC-0, décision D3 encore ouverte).

Le second correctif est donc délibérément **déterministe** : les chunks du
corpus commencent par leur titre de section (« 3. Définitions\\n\\n… »), et
c'est ce titre qui sert à les choisir. Le résultat ne dépend d'aucun score, donc
ne bougera pas quand D3 sera tranchée.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.course_plan import (
    LESSON_SECTIONS,
    Section,
    sources_absentes,
    texte_releve_de_la_section,
    titre_de_section,
)

from . import assertions
from .cas import par_id, tous_les_cas

CAS_12 = par_id(tous_les_cas())[12]


def _course_planner(resultat) -> dict:
    return next(e for e in resultat.node_trace if e["node"] == "course_planner")


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_ouvre_bien_sur_l_introduction(agent_qa, session_eleve):
    """Le découpage section par section n'est pas remis en cause par le correctif."""
    resultat = await agent_qa.respond(CAS_12.prompt, {"serie": "S2"}, session_eleve)

    entree = _course_planner(resultat)
    assert entree["section"] == "introduction"
    assert entree["chapitre"] == "Les Nombres Complexes"


async def test_le_prompt_exact_sert_la_definition_fondatrice(agent_qa, session_eleve):
    """Le cœur du cas : la définition doit être disponible dès le premier tour."""
    resultat = await agent_qa.respond(CAS_12.prompt, {"serie": "S2"}, session_eleve)

    servies = _course_planner(resultat)["sections_servies"]
    assert any("Définitions" in titre for titre in servies), (
        f"aucune section de définitions servie au premier tour : {servies}"
    )


async def test_la_definition_atteint_reellement_le_prompt(agent_qa, session_eleve):
    """Assertion sur le texte du corpus, pas sur la prose du modèle.

    C'est ce que la couche A peut prouver ici : le contenu est *disponible*.
    Qu'il soit effectivement restitué relève de la couche B, donc de D2.
    """
    prepared = await agent_qa.prepare(CAS_12.prompt, {"serie": "S2"}, session_eleve)

    assert "3. Définitions" in prepared.final_prompt
    assert "Définition 1" in prepared.final_prompt
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


async def test_la_consigne_n_interdit_plus_les_definitions(agent_qa, session_eleve):
    """La formulation qui produisait le bug ne doit pas revenir."""
    prepared = await agent_qa.prepare(CAS_12.prompt, {"serie": "S2"}, session_eleve)

    assert "N'entre pas encore dans les définitions formelles" not in prepared.final_prompt


# --- Au-delà du prompt exact -------------------------------------------------


def test_chaque_etape_du_plan_declare_ses_sources():
    """Sans sources déclarées, l'ancrage déterministe ne s'applique pas."""
    for section in LESSON_SECTIONS:
        assert section.sources, f"étape sans sources déclarées : {section.key}"


def test_l_introduction_porte_bien_la_definition_dans_ses_sources():
    introduction = LESSON_SECTIONS[0]
    assert "Définitions" in introduction.sources


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("3. Définitions\n\n**Définition 1 (Nombre complexe).**", "Définitions"),
        ("11. Exercices\n\n### Faciles", "Exercices"),
        ("9. Erreurs fréquentes\n\n- Confondre", "Erreurs fréquentes"),
        ("# Leçon Pilote — Les Nombres Complexes", None),
        ("du texte sans titre numéroté", None),
    ],
)
def test_le_titre_de_section_est_lu_sur_le_chunk(texte, attendu):
    assert titre_de_section(texte) == attendu


def test_la_liaison_tolere_l_accord_et_les_mots_en_plus():
    """« 9. Erreurs fréquentes » doit répondre à la source « Erreurs fréquentes »."""
    erreurs = next(s for s in LESSON_SECTIONS if s.key == "erreurs")

    assert texte_releve_de_la_section("9. Erreurs fréquentes\n\n- …", erreurs) is True
    assert texte_releve_de_la_section("10. Astuces\n\n- …", erreurs) is True
    assert texte_releve_de_la_section("3. Définitions\n\n…", erreurs) is False


def test_une_section_sans_sources_ne_reclame_rien():
    """Garde-fou : le mécanisme est opt-in, il ne s'impose pas partout."""
    muette = Section("x", "X", "instruction")

    assert texte_releve_de_la_section("3. Définitions\n\n…", muette) is False
    assert sources_absentes([], muette) == []


def test_sources_absentes_ne_signale_que_ce_qui_manque():
    introduction = LESSON_SECTIONS[0]

    assert sources_absentes(["Introduction", "Définitions"], introduction) == []
    assert sources_absentes(["Introduction"], introduction) == ["Définitions"]


# --- Non-régression : ne pas fabriquer d'ancrage -----------------------------
# Le risque propre à ce correctif est d'aller chercher du contenu à tout prix.
# Les fixtures #50 à #52 valident exactement l'inverse : savoir dire « je ne l'ai
# pas ». Le mécanisme ne s'arme que si un chapitre a pu être lié à la demande.


@pytest.mark.parametrize(
    "question",
    [
        "Fais-moi un cours sur les suites numériques",   # fixture positive #50
        "Donne-moi les inégalités remarquables",         # fixture positive #51
        "Exercice sur les suites numeriques",            # fixture positive #52
    ],
)
async def test_un_chapitre_absent_ne_declenche_aucun_ancrage(
    question, agent_qa, session_eleve
):
    """Aucun chapitre lié → aucune recherche ciblée, donc aucun faux ancrage."""
    resultat = await agent_qa.respond(question, {"serie": "S2"}, session_eleve)

    entree = next((e for e in resultat.node_trace if e["node"] == "course_planner"), None)
    if entree is None:      # la question n'est pas partie en mode cours
        return
    assert entree["chapitre"] != "Les Nombres Complexes", (
        "un chapitre sans rapport a été substitué à la demande de l'élève"
    )
