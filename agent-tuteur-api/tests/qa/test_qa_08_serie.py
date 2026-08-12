"""Cas QA #8 — « je suis en classe de terminale » (testeuse : Marie Paul Basse).

Observé : l'agent affirme que l'élève est en S1 alors qu'elle a précisé S2, et
persiste après deux corrections explicites.

Le prompt du testeur ne nomme **aucune** série : c'est la moitié souvent
oubliée du cas. Deux règles non-négociables se rencontrent ici et tirent en
sens inverse :

* n°3 — ne jamais halluciner de contexte élève : sans déclaration, aucune série
  ne doit être attribuée. C'est ce vide que l'agent comblait par « S1 » ;
* n°5 — une correction explicite est retenue immédiatement et pour toute la
  session, donc elle prime sur la série du profil du compte.

Les assertions portent sur la décision du nœud ``profil_eleve`` et sur le
prompt assemblé (tous deux produits par le code), jamais sur la prose.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.profil import detecter_serie

from . import assertions
from .cas import par_id, tous_les_cas

CAS_08 = par_id(tous_les_cas())[8]

#: Profil du compte, délibérément faux : c'est la situation du cas, où l'élève
#: est enregistrée en S1 et doit pouvoir se corriger.
PROFIL_ERRONE = {"serie": "S1"}


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_ne_fabrique_aucune_serie(agent_qa, session_eleve):
    """« Je suis en classe de terminale » ne nomme pas de série : aucune retenue.

    Sans profil, l'absence doit rester une absence. C'est la cause première du
    cas #8 : l'agent a comblé ce vide tout seul.
    """
    resultat = await agent_qa.respond(CAS_08.prompt, {}, session_eleve)

    assertions.assert_serie_effective(resultat, None)
    assert session_eleve.serie is None, "une série a été mémorisée sans déclaration"


async def test_le_prompt_exact_n_annonce_aucune_serie_a_l_eleve(agent_qa, session_eleve):
    """Rien n'est annoncé à l'élève non plus — vérifié sur le prompt assemblé."""
    prepared = await agent_qa.prepare(CAS_08.prompt, {}, session_eleve)

    assertions.assert_aucune_serie_annoncee(prepared)


async def test_le_profil_du_compte_reste_utilise_faute_de_declaration(agent_qa, session_eleve):
    """Ne pas inventer n'est pas ignorer : un profil existant s'applique.

    Contrôle de non-régression du correctif lui-même — il serait facile de
    « corriger » le cas #8 en cessant tout bonnement d'utiliser la série.
    """
    resultat = await agent_qa.respond(CAS_08.prompt, PROFIL_ERRONE, session_eleve)

    assertions.assert_serie_effective(resultat, "S1")


# --- La correction explicite (cœur du cas) -----------------------------------


async def test_une_correction_explicite_prime_sur_le_profil(agent_qa, session_eleve):
    """Tour 1 : le prompt du testeur. Tour 2 : la correction. Elle gagne.

    Le contexte curriculaire continue d'annoncer S1 à chaque appel — c'est bien
    le propre du bug : le profil du compte reprenait la main.
    """
    await agent_qa.respond(CAS_08.prompt, PROFIL_ERRONE, session_eleve)
    resultat = await agent_qa.respond("je suis en S2", PROFIL_ERRONE, session_eleve)

    assertions.assert_serie_effective(resultat, "S2")
    assert session_eleve.serie == "S2"


async def test_la_correction_survit_aux_tours_suivants(agent_qa, session_eleve):
    """« Durablement dans la session » : c'est le mot ``persiste`` du rapport."""
    await agent_qa.respond("je suis en S2", PROFIL_ERRONE, session_eleve)

    for question in ("Comment calculer le module d'un nombre complexe ?",
                     "et le conjugué ?",
                     "merci"):
        resultat = await agent_qa.respond(question, PROFIL_ERRONE, session_eleve)
        assertions.assert_serie_effective(resultat, "S2")


async def test_deux_corrections_successives_la_derniere_gagne(agent_qa, session_eleve):
    """Le rapport parle de deux corrections explicites ignorées."""
    await agent_qa.respond(CAS_08.prompt, PROFIL_ERRONE, session_eleve)
    await agent_qa.respond("je suis en S2", PROFIL_ERRONE, session_eleve)
    resultat = await agent_qa.respond("non plutôt S3", PROFIL_ERRONE, session_eleve)

    assertions.assert_serie_effective(resultat, "S3")
    assert session_eleve.serie == "S3"


async def test_la_serie_corrigee_atteint_le_prompt(agent_qa, session_eleve):
    """La correction doit gouverner le cadre annoncé, pas seulement l'état."""
    await agent_qa.respond("je suis en S2", PROFIL_ERRONE, session_eleve)
    prepared = await agent_qa.prepare(
        "Comment calculer le module d'un nombre complexe ?", PROFIL_ERRONE, session_eleve
    )

    assertions.assert_serie_dans_le_cadre(prepared, "S2")
    assert "serie=S1" not in prepared.final_prompt, "la série erronée du profil a survécu"


# --- Au-delà du prompt exact (l'anti-pattern du CLAUDE.md) -------------------


@pytest.mark.parametrize(
    ("declaration", "attendue"),
    [
        ("je suis en S2", "S2"),
        ("je suis en terminale S2", "S2"),
        ("non, je suis en S2", "S2"),
        ("non plutôt S2", "S2"),
        ("ma série c'est S2", "S2"),
        ("je suis en TS2", "S2"),          # alias de nomenclature
        ("je suis en STIDD1", "T1"),       # ancienne ↔ nouvelle nomenclature
        ("je suis en s2", "S2"),           # minuscules
        ("je suis en série S1", "S1"),
        ("je suis en L2", "L2"),
    ],
)
def test_les_tournures_de_declaration_sont_reconnues(declaration, attendue):
    assert detecter_serie(declaration) == attendue


@pytest.mark.parametrize(
    "sans_declaration",
    [
        "je suis en classe de terminale",          # le prompt du cas
        "je ne suis pas en S1",                    # dire ce qu'on n'est pas
        "calcule S2 pour la suite définie par u_n",  # S2 = terme d'une suite
        "Quelle est la dérivée de x^2 ?",
        "Comment calculer le module d'un nombre complexe ?",
    ],
)
def test_aucune_serie_n_est_devinee(sans_declaration):
    """Le faux positif est le vrai danger : il réécrirait le profil en silence."""
    assert detecter_serie(sans_declaration) is None


async def test_un_exercice_mentionnant_s2_n_ecrase_pas_la_serie(agent_qa, session_eleve):
    """Non-régression du correctif : « S2 » dans un énoncé n'est pas une série."""
    await agent_qa.respond("je suis en S3", PROFIL_ERRONE, session_eleve)
    resultat = await agent_qa.respond(
        "calcule S2 pour la suite définie par u_n = 2n + 1", PROFIL_ERRONE, session_eleve
    )

    assertions.assert_serie_effective(resultat, "S3")


async def test_le_chemin_streaming_resout_la_serie_aussi(agent_qa, session_eleve):
    """``prepare`` est le chemin réellement emprunté par l'API (SSE)."""
    await agent_qa.respond("je suis en S2", PROFIL_ERRONE, session_eleve)
    prepared = await agent_qa.prepare("et le conjugué ?", PROFIL_ERRONE, session_eleve)

    assertions.assert_trace_compatible_avec_le_streaming(prepared)
    assertions.assert_serie_dans_le_cadre(prepared, "S2")


async def test_une_session_neuve_ne_herite_pas_de_la_correction(agent_qa):
    """L'état est bien *de session*, pas global — deux élèves ne se mélangent pas."""
    premiere = SessionState(student_id="eleve-a", tenant_id="qa")
    await agent_qa.respond("je suis en S2", PROFIL_ERRONE, premiere)

    seconde = SessionState(student_id="eleve-b", tenant_id="qa")
    resultat = await agent_qa.respond(CAS_08.prompt, PROFIL_ERRONE, seconde)

    assertions.assert_serie_effective(resultat, "S1")
    assert seconde.serie is None
