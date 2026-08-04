"""Génération et correction de quiz (porté de NURU `quiz_agent.py`).

Le principe défendu par ces tests : **jamais de contenu factice affiché à
l'élève**. Un quiz absent est acceptable, un quiz aux propositions
« Option 1 / Option 2 » ne l'est pas.
"""

import json

import pytest

from agent_tuteur.agent.llm.base import BaseLLM, LLMError
from agent_tuteur.agent.quiz import (
    QuizInvalide,
    analyser_reponse_quiz,
    contient_du_factice,
    corriger_quiz,
    generer_quiz,
)

QUIZ_VALIDE = {
    "question": "Quelle est la dérivée de $x^2$ ?",
    "choices": [
        {"id": "A", "text": "$2x$"},
        {"id": "B", "text": "$x$"},
        {"id": "C", "text": "$x^3/3$"},
        {"id": "D", "text": "$2$"},
    ],
    "correct_answer": "A",
    "explanation": "On applique la formule de dérivation des puissances.",
}


class _LLMScripte(BaseLLM):
    """Modèle factice qui débite des réponses préparées, une par appel."""

    name = "scripte"

    def __init__(self, reponses):
        self._reponses = list(reponses)
        self.appels = 0

    def available(self) -> bool:
        return True

    async def generate(self, prompt, *, system=None):
        self.appels += 1
        if not self._reponses:
            raise LLMError("plus de réponse scriptée")
        reponse = self._reponses.pop(0)
        if isinstance(reponse, Exception):
            raise reponse
        return reponse

    async def generate_stream(self, prompt, *, system=None):
        yield await self.generate(prompt, system=system)


# --- Analyse de la réponse du modèle ------------------------------------------


def test_un_quiz_bien_forme_est_accepte():
    analyse = analyser_reponse_quiz(json.dumps(QUIZ_VALIDE))
    assert analyse is not None
    assert analyse["correct_answer"] == "A"


def test_le_json_est_extrait_meme_entoure_de_texte():
    """Le modèle ajoute très souvent des balises markdown ou un préambule."""
    brut = f"Voici le quiz :\n```json\n{json.dumps(QUIZ_VALIDE)}\n```\nBon courage !"
    assert analyser_reponse_quiz(brut) is not None


@pytest.mark.parametrize(
    "brut",
    [
        "",
        "pas de json ici",
        "{ceci n'est pas du json}",
    ],
)
def test_une_reponse_illisible_est_rejetee(brut):
    assert analyser_reponse_quiz(brut) is None


def test_un_quiz_a_une_seule_proposition_est_rejete():
    invalide = {**QUIZ_VALIDE, "choices": [{"id": "A", "text": "$2x$"}]}
    assert analyser_reponse_quiz(json.dumps(invalide)) is None


def test_une_bonne_reponse_qui_ne_designe_aucune_proposition_est_rejetee():
    """Cas réel : le modèle répond « E » alors que les choix vont de A à D."""
    invalide = {**QUIZ_VALIDE, "correct_answer": "E"}
    assert analyser_reponse_quiz(json.dumps(invalide)) is None


def test_une_proposition_sans_texte_est_rejetee():
    invalide = {**QUIZ_VALIDE, "choices": [{"id": "A", "text": ""}, {"id": "B", "text": "x"}]}
    assert analyser_reponse_quiz(json.dumps(invalide)) is None


# --- Cohérence de l'explication -----------------------------------------------


def test_l_explication_designe_toujours_la_bonne_reponse():
    """Le modèle produit parfois un JSON valide dont l'explication se contredit."""
    incoherent = {**QUIZ_VALIDE, "explanation": "En effet, $x$ est la dérivée cherchée."}
    analyse = analyser_reponse_quiz(json.dumps(incoherent))
    # L'explication trompeuse (qui justifie B) est écartée au profit de la
    # phrase canonique construite depuis correct_answer.
    assert analyse["explanation"] == "La bonne réponse est A : $2x$."


def test_une_explication_qui_cite_la_bonne_proposition_est_conservee():
    citante = {**QUIZ_VALIDE, "explanation": "La dérivée de $x^2$ vaut $2x$ par la règle des puissances."}
    analyse = analyser_reponse_quiz(json.dumps(citante))
    assert analyse["explanation"].startswith("La bonne réponse est A : $2x$.")
    assert "règle des puissances" in analyse["explanation"]


def test_une_explication_generique_est_ecartee_au_profit_de_la_phrase_canonique():
    """Comportement de NURU, porté tel quel — voir « Points à valider » (V5).

    L'explication n'est gardée que si elle **cite** le texte de la bonne
    proposition. Ici « On applique la formule de dérivation des puissances »
    est juste, mais ne cite pas « $2x$ » : elle est donc écartée. Règle
    prudente, mais qui fait perdre du contenu utile.
    """
    analyse = analyser_reponse_quiz(json.dumps(QUIZ_VALIDE))
    assert analyse["explanation"] == "La bonne réponse est A : $2x$."


def test_une_explication_absente_est_remplacee_par_la_phrase_canonique():
    sans = {**QUIZ_VALIDE, "explanation": ""}
    analyse = analyser_reponse_quiz(json.dumps(sans))
    assert analyse["explanation"] == "La bonne réponse est A : $2x$."


# --- Détection du contenu factice ---------------------------------------------


@pytest.mark.parametrize("factice", ["Option 1", "Définition incorrecte 2", "placeholder"])
def test_le_contenu_de_remplissage_est_detecte(factice):
    quiz = {**QUIZ_VALIDE, "choices": [{"id": "A", "text": factice}, {"id": "B", "text": "$2x$"}]}
    assert contient_du_factice(quiz) is True


def test_un_vrai_quiz_n_est_pas_pris_pour_du_factice():
    assert contient_du_factice(QUIZ_VALIDE) is False


# --- Génération complète -------------------------------------------------------


async def test_un_quiz_valide_est_renvoye():
    llm = _LLMScripte([json.dumps(QUIZ_VALIDE)])
    quiz = await generer_quiz(llm, "Dérivation")
    assert quiz.est_utilisable
    assert len(quiz.questions) == 1
    assert llm.appels == 1


async def test_une_reponse_invalide_declenche_une_seconde_tentative():
    llm = _LLMScripte(["n'importe quoi", json.dumps(QUIZ_VALIDE)])
    quiz = await generer_quiz(llm, "Dérivation")
    assert quiz.est_utilisable
    assert llm.appels == 2


async def test_apres_tous_les_essais_le_quiz_est_vide_et_non_factice():
    """Le point central : on préfère avouer l'échec à afficher du remplissage."""
    llm = _LLMScripte(["raté", "encore raté"])
    quiz = await generer_quiz(llm, "Dérivation")

    assert quiz.est_utilisable is False
    assert quiz.questions == []
    assert "n'a pas pu être généré" in quiz.to_dict()["instructions"]


async def test_un_quiz_factice_n_est_jamais_renvoye():
    factice = {
        **QUIZ_VALIDE,
        "choices": [{"id": "A", "text": "Option 1"}, {"id": "B", "text": "Option 2"}],
    }
    llm = _LLMScripte([json.dumps(factice), json.dumps(factice)])
    quiz = await generer_quiz(llm, "Dérivation")
    assert quiz.est_utilisable is False


async def test_une_panne_du_modele_n_interrompt_pas_le_service():
    llm = _LLMScripte([LLMError("service indisponible"), json.dumps(QUIZ_VALIDE)])
    quiz = await generer_quiz(llm, "Dérivation")
    assert quiz.est_utilisable


async def test_un_type_de_quiz_inconnu_est_refuse():
    with pytest.raises(QuizInvalide):
        await generer_quiz(_LLMScripte([]), "Dérivation", quiz_type="dissertation")


# --- Correction ----------------------------------------------------------------


def test_une_bonne_reponse_est_reconnue():
    correction = corriger_quiz(QUIZ_VALIDE, "A")
    assert correction["is_correct"] is True
    assert correction["score"] == 1.0


def test_une_mauvaise_reponse_est_reconnue():
    correction = corriger_quiz(QUIZ_VALIDE, "C")
    assert correction["is_correct"] is False
    assert correction["score"] == 0.0
    assert correction["correct_answer"] == "A"


def test_la_correction_tolere_la_casse_et_les_espaces():
    assert corriger_quiz(QUIZ_VALIDE, " a ")["is_correct"] is True


def test_une_reponse_vide_est_fausse_sans_planter():
    assert corriger_quiz(QUIZ_VALIDE, "")["is_correct"] is False
    assert corriger_quiz(QUIZ_VALIDE, None)["is_correct"] is False
