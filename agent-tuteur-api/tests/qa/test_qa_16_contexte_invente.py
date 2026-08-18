"""Cas QA #16 — « C'est quoi la différence entre forme algébrique,
trigonométrique et exponentielle ? » (Ahmed Souleymane).

Observé : l'agent affirme à l'élève qu'il a « déjà étudié les nombres complexes
en série S2/S4 ». L'élève n'a jamais donné sa série, ni dit ce qu'il avait vu.
Règle non-négociable n°3.

Cause racine mesurée : ce n'était pas une invention du modèle, **c'est nous qui
la lui fournissions**. Le bloc de documentation injecté dans le prompt attribuait
chaque extrait avec ``source_label``, qui porte le nom de fichier du corpus ::

    [Réf. interne 1 — Lecon_01_Nombres_Complexes_TS2S4.md — Les Nombres Complexes]

« TS2S4 » y est une métadonnée de *document*. Rien dans ce bloc ne le distingue
d'un fait sur l'élève, et le modèle l'a lu comme tel. Sondé sur le prompt exact,
c'était l'**unique** marqueur de série de tout le ``final_prompt`` : les cinq
extraits servis n'en contenaient aucun autre.

Correctif structurel, en deux moitiés qui répondent à deux fuites distinctes :

* le nom de fichier ne part plus au modèle — ``build_context_block`` attribue
  désormais par ``libelle_interne`` (le chapitre). Ce qui reste suffit à ancrer
  la réponse, et l'attribution complète continue d'être servie au client par
  ``trace["sources"]``, qui n'est pas dégradée ;
* le corps même des leçons porte parfois « Terminale S2/S4 » (ligne de titre,
  tableau d'en-tête). Retirer le nom de fichier ne peut donc pas suffire : les
  règles communes aux deux personas disent maintenant que la documentation
  décrit un chapitre et n'apprend rien sur l'élève.

Ce que la couche A prouve ici : aucune identité de document ne part au modèle,
et l'attribution client survit. Que la prose n'attribue plus de série à l'élève
quand un extrait en contient une relève de la couche B, donc de D2.
"""

from __future__ import annotations

import re

import pytest

from agent_tuteur.agent.prompt import build_context_block

from . import assertions
from .cas import cas_positifs, par_id, tous_les_cas

CAS_16 = par_id(tous_les_cas())[16]

#: Marqueurs de série tels qu'ils apparaissent dans les **noms de fichier** du
#: corpus. Volontairement sans ``\b`` : dans « Lecon_01_..._TS2S4.md », le motif
#: est collé à des soulignés, qui sont des caractères de mot — une frontière de
#: mot ne l'aurait jamais trouvé, et le test aurait été vert sans rien prouver.
MARQUEUR_DE_SERIE = re.compile(r"TS2S4|TS1S3|TS2|TS1|TL\b", re.IGNORECASE)


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_ne_porte_aucune_identite_de_document(agent_qa, session_eleve):
    """Le cœur du cas : le nom de fichier n'atteint plus le modèle.

    Rejoué **sans contexte curriculaire** — c'est la situation d'Ahmed, qui
    n'avait rien déclaré. Toute mention de série dans le prompt ne peut donc
    venir que du corpus.
    """
    prepared = await agent_qa.prepare(CAS_16.prompt, {}, session_eleve)

    fichiers = {
        sc.chunk.metadata.source_document
        for sc in prepared.retrieved
        if sc.chunk.metadata.source_document
    }
    assert fichiers, "aucun extrait servi : le cas ne prouverait rien"
    for fichier in fichiers:
        assert fichier not in prepared.final_prompt, (
            f"nom de fichier du corpus envoyé au modèle : {fichier}"
        )


async def test_le_prompt_exact_n_annonce_aucune_serie(agent_qa, session_eleve):
    """Aucun marqueur de série, d'où qu'il vienne, dans le prompt final."""
    prepared = await agent_qa.prepare(CAS_16.prompt, {}, session_eleve)

    trouves = MARQUEUR_DE_SERIE.findall(prepared.final_prompt)
    assert not trouves, f"marqueurs de série servis au modèle : {trouves}"
    assertions.assert_aucune_serie_annoncee(prepared)
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


async def test_l_attribution_cote_client_n_est_pas_degradee(agent_qa, session_eleve):
    """La contrepartie : on retire au modèle, pas à l'élève.

    ``trace["sources"]`` alimente l'onglet sources du frontend, où la provenance
    (quel fichier) est une information légitime. Un correctif qui l'aurait
    vidée aurait « réglé » le cas en cassant l'attribution.
    """
    prepared = await agent_qa.prepare(CAS_16.prompt, {}, session_eleve)

    labels = [s["label"] for s in prepared.trace["sources"]]
    assert labels, "aucune source attribuée"
    assert all(".md" in label for label in labels), (
        f"le nom de fichier a disparu de l'attribution client : {labels}"
    )


# --- Au-delà du prompt exact -------------------------------------------------
# La cause est dans l'assembleur de contexte, pas dans cette question-là : elle
# se reproduit sur **tout** tour qui sert un extrait, quelle que soit l'intention.


@pytest.mark.parametrize(
    "question",
    [
        "C'est quoi la différence entre forme algébrique, trigonométrique et exponentielle ?",
        "Fais-moi un cours sur les nombres complexes",       # branche cours
        "Je ne comprends pas les dérivées",                  # branche cours (cas #14)
        "z = 3 + 4i, donne la partie réelle et le module",   # branche exercice + outil
        "Teste-moi sur les nombres complexes",               # branche quiz
    ],
)
async def test_aucune_branche_ne_livre_le_nom_de_fichier(question, agent_qa, session_eleve):
    prepared = await agent_qa.prepare(question, {}, session_eleve)

    for sc in prepared.retrieved:
        fichier = sc.chunk.metadata.source_document
        if fichier:
            assert fichier not in prepared.final_prompt, (
                f"{fichier} servi au modèle sur {question!r}"
            )


def test_le_bloc_de_contexte_attribue_par_chapitre(agent_qa):
    """L'unité du correctif, isolée de tout le pipeline."""
    extraits = agent_qa._retriever.retrieve("nombres complexes", {}, top_k=3)
    assert extraits, "corpus vide : le test ne prouverait rien"

    bloc = build_context_block(extraits)
    for sc in extraits:
        assert sc.libelle_interne in bloc
        assert sc.chunk.metadata.source_document not in bloc


def test_le_libelle_interne_se_replie_sans_inventer():
    """Un chunk sans chapitre ne doit pas faire réapparaître le fichier."""
    from agent_tuteur.domain.models import Chunk, CurriculumMetadata, ScoredChunk

    nu = ScoredChunk(
        chunk=Chunk(
            id="c1",
            text="t",
            metadata=CurriculumMetadata(
                niveau="Terminale", serie="S2", source_document="Lecon_01_X_TS2S4.md"
            ),
        ),
        score=0.5,
    )
    assert "TS2S4" not in nu.libelle_interne
    assert "Lecon" not in nu.libelle_interne
    # …et l'attribution client, elle, la conserve.
    assert "Lecon_01_X_TS2S4.md" in nu.source_label


# --- Non-régression ----------------------------------------------------------


@pytest.mark.parametrize("cas", cas_positifs(), ids=[c.identifiant_test for c in cas_positifs()])
async def test_aucune_fixture_positive_ne_recoit_de_nom_de_fichier(cas, agent_qa, session_eleve):
    """Les 13 comportements validés, rejoués sans série déclarée."""
    prepared = await agent_qa.prepare(cas.prompt, {}, session_eleve)

    for sc in prepared.retrieved:
        fichier = sc.chunk.metadata.source_document
        if fichier:
            assert fichier not in prepared.final_prompt


async def test_une_serie_reellement_declaree_reste_annoncee(agent_qa, session_eleve):
    """La contrepartie du cas #8 : taire le document ne doit pas taire l'élève.

    Ce que la règle n°3 interdit est d'*inventer* un cadre, pas d'utiliser celui
    que l'élève a donné. Un correctif qui aurait effacé les deux serait une
    régression sur le cas #8, déjà clos.
    """
    prepared = await agent_qa.prepare(CAS_16.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_serie_dans_le_cadre(prepared, "S2")
