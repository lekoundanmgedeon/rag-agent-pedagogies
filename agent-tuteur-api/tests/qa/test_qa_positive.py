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


