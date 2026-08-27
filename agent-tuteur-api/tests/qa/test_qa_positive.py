"""Fixtures de non-régression — `qa/qa_cases_positive.json` (13 comportements validés).

Ces cas ne décrivent pas des bugs mais des comportements **déjà confirmés par un
testeur**. Ils tournent à chaque correctif, dans la même suite, pour attraper la
dégradation collatérale.

Ce que la couche A peut geler ici, et ce qu'elle ne peut pas, est explicite
(``COUVERTS_COUCHE_A`` / ``COUCHE_B_SEULEMENT``) : la majorité de ces
comportements sont des *refus formulés par le modèle*, qu'aucune assertion
déterministe ne peut vérifier tant que le refus n'est pas décidé avant la
génération. Le dire dans le code évite de croire ces cas gelés alors qu'ils ne le
sont pas.
"""

from __future__ import annotations

import pytest

from . import assertions
from .assertions import NOEUD_RETRIEVAL
from .cas import cas_positifs

CAS = cas_positifs()

#: Cas dont le comportement confirmé est vérifiable hors-ligne, sur une décision
#: du pipeline (routage, retrieval) plutôt que sur la prose du modèle.
#: 50/51/52 : hors-périmètre honnêtement signalé → observable sur le retrieval.
COUVERTS_COUCHE_A = {50, 51, 52}

#: Cas dont le comportement confirmé n'existe aujourd'hui que dans le texte
#: généré. Ils ne sont **pas** gelés en CI ; seule la couche B les rejoue.
#: 49/54/55/56 : exactitude mathématique en prose. 53/57/58/59/60/61 : refus.
COUCHE_B_SEULEMENT = {49, 53, 54, 55, 56, 57, 58, 59, 60, 61}


def test_les_13_fixtures_sont_presentes_et_intactes():
    assert len(CAS) == 13
    assert {c.id for c in CAS} == set(range(49, 62))
    assert all(c.prompt.strip() and c.confirmed_behavior for c in CAS)


def test_la_couverture_declaree_partitionne_les_13_cas():
    """Aucun cas positif ne tombe entre les deux couches sans qu'on le sache."""
    assert {c.id for c in CAS} == COUVERTS_COUCHE_A | COUCHE_B_SEULEMENT
    assert not COUVERTS_COUCHE_A & COUCHE_B_SEULEMENT



# --- Non-régression du court-circuit de sécurité (cas QA #7) ------------------
# Le routage de détresse s'exécute AVANT tout le reste : un faux positif y
# détournerait n'importe lequel de ces 13 comportements validés vers un message
# d'aide. C'est le risque de régression n°1 du correctif, en particulier sur les
# cas 57 à 61 (tricherie, sujet sensible, hors-sujet), qui emploient un registre
# émotionnel proche.
@pytest.mark.parametrize("cas", CAS, ids=[c.identifiant_test for c in CAS])
async def test_aucun_faux_positif_de_detresse(cas, agent_qa, session_eleve):
    resultat = await agent_qa.respond(cas.prompt, {"serie": "S2"}, session_eleve)
    assertions.assert_aucun_court_circuit_securite(resultat)


# --- Non-régression du routeur méta (cas QA #2/#3/#4) -------------------------
# Le routeur méta s'exécute juste après detect_intent et supprime le retrieval.
# Aucun de ces 13 comportements validés n'est une question sur le service : les
# absorber priverait l'agent du corpus sur des cas où il répondait correctement,
# notamment 50/51/52 dont le mérite est précisément de savoir dire « je ne l'ai
# pas » APRÈS avoir cherché.
@pytest.mark.parametrize("cas", CAS, ids=[c.identifiant_test for c in CAS])
async def test_aucun_faux_positif_du_routeur_meta(cas, agent_qa, session_eleve):
    resultat = await agent_qa.respond(cas.prompt, {"serie": "S2"}, session_eleve)
    entree = next((e for e in resultat.node_trace if e["node"] == "detect_intent"), None)
    assert entree is not None
    assert entree["intent"] != "meta", f"question de contenu absorbée par le routeur méta : {cas.prompt!r}"
    # Le corpus doit être **interrogé** — c'est ce que le routeur méta
    # supprimait. Ce qu'il en reste, en revanche, peut légitimement être vide :
    # depuis le contrôle de couverture des tours conceptuels (cas #29/#30), une
    # notion absente de tous les chapitres indexés fait écarter les extraits au
    # lieu de servir les moins mauvais. Sur le corpus figé à deux chapitres,
    # c'est le cas de #49, #51, #54 et #59 — et pour #51 (« inégalités
    # remarquables »), c'est précisément le comportement que la testeuse avait
    # validé : « l'agent indique honnêtement l'absence d'information ».
    recherche = next((e for e in resultat.node_trace if e["node"] == NOEUD_RETRIEVAL), None)
    assert recherche is not None, "le corpus n'a pas été interrogé sur une question de contenu"
