"""Cas QA #26 et #27 — deux demandes d'orientation traitées comme du contenu.

- **#26** « Listes moi les chapitres du cours de maths en terminale S1 » (Rahma) :
  « reformulée plusieurs fois, la demande obtient des réponses de qualité
  variable ». Mesuré : la phrase tombait en mode **COURS** — le mot « cours » y
  déclenchait ``_COURSE_START`` — donc en ouverture de chapitre sur une demande
  d'inventaire, chapitre non identifié. La variabilité n'était pas un aléa de
  génération : selon la formulation, ce n'était pas la même branche du graphe.
- **#27** « Aide moi à devenir meilleure en Mathématique. » (Rafiatou) : réponse
  « sans rapport » (« qu'est-ce que tu veux faire avec cette équation »).
  Mesuré : intention ``exercice`` par défaut, niveau d'indice 1 sur cinq
  extraits pris au hasard — la relance portait donc sur un énoncé que la
  testeuse n'avait jamais donné (règle non-négociable n°3).

Les deux se règlent par le routage, et le #26 en plus par une réponse **écrite
par le code** : un inventaire de chapitres doit être exact et identique d'un
tour à l'autre, ce qu'aucune prose échantillonnée ne garantit (doctrine D5).
"""

from __future__ import annotations

from agent_tuteur.agent.intent import Intent, classify_intent
from agent_tuteur.agent.prompt import CONSIGNE_DEMANDE_OUVERTE

from . import assertions
from .cas import par_id, tous_les_cas

CAS = par_id(tous_les_cas())
CHAPITRES_INDEXES = {"Les Nombres Complexes", "Le Calcul Intégral"}


# --- Cas 26 — inventaire des chapitres ---------------------------------------


def test_une_demande_d_inventaire_ne_part_plus_en_cours():
    """La cause racine mesurée, gelée : « cours de maths » n'ouvre pas un cours."""
    for question in (
        CAS[26].prompt,
        "liste-moi les chapitres disponibles",
        "donne-moi la liste des leçons que tu as",
        "c'est quoi les chapitres que tu connais ?",
        "quels chapitres peux-tu m'enseigner ?",
    ):
        assert classify_intent(question).intent == Intent.META, question


async def test_l_inventaire_est_identique_a_chaque_rejeu(agent_qa, session_eleve):
    """« Réponses de qualité variable » : ici, deux rejeux, un seul texte.

    L'assertion textuelle est permise parce que la réponse est court-circuitée,
    donc produite par le code — c'est la seule catégorie de texte que le rejeu
    QA s'autorise à comparer mot pour mot.
    """
    premier = await agent_qa.respond(CAS[26].prompt, {"serie": "S2"}, session_eleve)
    second = await agent_qa.respond(
        "quels sont les chapitres disponibles ?", {"serie": "S2"}, session_eleve
    )
    assertions.assert_intention(premier, "meta")
    assertions.assert_pas_de_retrieval(premier)
    assert premier.answer == second.answer, "deux formulations, deux réponses"


async def test_l_inventaire_annonce_tous_les_chapitres_et_rien_d_autre(agent_qa, session_eleve):
    """Règles n°3 et n°4 portées par le code, pas par une consigne de prompt."""
    resultat = await agent_qa.respond(CAS[26].prompt, {"serie": "S2"}, session_eleve)
    for chapitre in CHAPITRES_INDEXES:
        assert chapitre in resultat.answer, f"chapitre indexé passé sous silence : {chapitre}"
    for invente in ("Suites Numériques", "Probabilités", "Trigonométrie"):
        assert invente not in resultat.answer, f"chapitre inventé : {invente}"
    # L'élève a demandé « mon programme … terminale S1 » : l'agent ne le connaît
    # pas, et doit le dire au lieu de faire passer sa couverture pour un programme.
    assert "programme officiel" in resultat.answer


async def test_l_inventaire_ne_sollicite_pas_le_modele(agent_qa, session_eleve):
    """Le court-circuit vaut aussi sur le chemin streamé, sans quoi la démo
    divergerait des tests — le défaut déjà rencontré sur l'ouverture de soutien.
    """
    prepared = await agent_qa.prepare(CAS[26].prompt, {"serie": "S2"}, session_eleve)
    assert prepared.reponse_directe is not None
    flux = "".join([token async for token in agent_qa.stream(prepared)])
    assert flux.strip() == prepared.reponse_directe.strip()
    assert prepared.generation["llm_provider"] == "code", (
        "un inventaire de chapitres n'est pas un tour de mise en sécurité : "
        "les deux court-circuitent le modèle, la trace doit les distinguer"
    )


# --- Cas 27 — demande d'aide sans objet nommé --------------------------------


async def test_une_demande_ouverte_est_orientee_et_non_socratisee(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS[27].prompt, {"serie": "S2"}, session_eleve)
    assertions.assert_intention(resultat, "meta")
    assertions.assert_pas_de_retrieval(resultat)
    assert CONSIGNE_DEMANDE_OUVERTE in resultat.final_prompt
    # Le prompt propose ce qui existe : la question de clarification a de quoi
    # s'appuyer, au lieu de porter sur un exercice jamais évoqué.
    for chapitre in CHAPITRES_INDEXES:
        assert chapitre in resultat.final_prompt


def test_une_demande_d_aide_avec_objet_reste_socratique():
    """Frontière : « aide-moi » ne suffit pas, c'est l'absence d'objet qui compte.

    Sans cette borne, la branche d'orientation absorberait les tours où l'élève
    travaille vraiment — et le tuteur cesserait de l'aider pour lui demander sur
    quoi il veut travailler alors qu'il vient de le dire.
    """
    for question in (
        "aide-moi sur cet exercice",
        "aide-moi à calculer cette intégrale",
        "aide-moi à comprendre les nombres complexes",
    ):
        assert classify_intent(question).intent != Intent.META, question
