"""Cas QA #17 — « Fais-moi l'étude de fonction de ln(x) » (Tony SARRE).

Observé : l'agent répond avec la **règle du quotient**, sans rapport avec la
question posée. Rangé par le backlog en « RAG — pertinence de récupération ».

Ce que la sonde a établi (cf. D4) : le cas est un **doublon du #9**, déjà clos —
même prompt à la virgule près, à la casse et au trait d'union près, remonté par
deux testeurs différents. Le correctif du #9 le couvre donc entièrement :
``etudier_la_demande`` établit l'étude symboliquement et
``escalade_pour_resultat_verifie`` la fait servir en « Solution directe » au lieu
d'une relance socratique.

Pourquoi ce fichier existe quand même, plutôt qu'une ligne dans celui du #9 :
l'attente du #17 n'est pas celle du #9. Le #9 reprochait une **relance
socratique** ; le #17 reproche un **contenu étranger**. Ce qui est vérifié ici
est donc que la réponse est ancrée sur l'étude vérifiée et non sur les extraits
remontés — qui sont, mesuré sur les deux embedders, cinq extraits « Le Calcul
Intégral ». Autrement dit : la pertinence du retrieval n'est pas ce qui sauve ce
tour, et il ne faut pas que le test laisse croire le contraire.

Ce que la couche A prouve ici : l'étude est établie, elle part au modèle, la
posture est directe, et rien n'oblige le modèle à se rabattre sur les extraits.
Que la prose déroule effectivement l'étude relève de la couche B, donc de D2.
"""

from __future__ import annotations

from agent_tuteur.textutil import strip_accents

from .cas import par_id, tous_les_cas

CAS_17 = par_id(tous_les_cas())[17]
CAS_09 = par_id(tous_les_cas())[9]


def test_le_cas_17_est_bien_le_meme_prompt_que_le_9():
    """Le fondement du classement en doublon, vérifié plutôt qu'affirmé.

    Les deux testeurs ont tapé la même phrase à la casse, aux accents et au
    trait d'union près — d'où la normalisation. Si un jour l'un des deux prompts
    change dans le backlog, ce test le dit, et la couverture par ricochet cesse
    d'être justifiée.
    """

    def aplatir(texte: str) -> str:
        return " ".join(strip_accents(texte.replace("-", " ").replace("’", "'")).lower().split())

    assert aplatir(CAS_17.prompt) == aplatir(CAS_09.prompt), (
        f"{CAS_17.prompt!r} vs {CAS_09.prompt!r}"
    )


async def test_le_prompt_exact_etablit_l_etude_symboliquement(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_17.prompt, {"serie": "S2"}, session_eleve)

    etude = resultat.trace["etude_fonction"]
    assert etude is not None, "aucune étude de fonction établie"
    assert etude["expression"] == "log(x)"
    assert etude["domaine"] == "]0 ; +∞["
    assert etude["derivee"] == "1/x"


async def test_le_prompt_exact_est_servi_directement(agent_qa, session_eleve):
    """Une étude est un livrable : pas de relance, pas de graduation."""
    resultat = await agent_qa.respond(CAS_17.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["hint_level"] == 4
    assert resultat.trace["hint_reason"] == "résultat vérifié et explicitement demandé"


async def test_la_reponse_n_est_pas_adossee_aux_extraits_remontes(agent_qa, session_eleve):
    """Le reproche exact du testeur : un contenu sans rapport avec la demande.

    Les extraits servis parlent d'intégrales — l'étude des fonctions n'est dans
    aucun chapitre indexé. Ce qui protège ce tour n'est donc pas la pertinence
    du retrieval mais le fait que la matière de la réponse soit **calculée** et
    présente dans le prompt, avec interdiction de la recalculer.
    """
    prepared = await agent_qa.prepare(CAS_17.prompt, {"serie": "S2"}, session_eleve)

    chapitres = {sc.chunk.metadata.chapitre for sc in prepared.retrieved}
    assert "Étude de fonctions" not in chapitres, (
        "le corpus a changé : ce test ne décrit plus l'index de la démo"
    )
    for attendu in ("Domaine de définition : ]0 ; +∞[", "f'(x) = 1/x", "ne les recalcule pas"):
        assert attendu in prepared.final_prompt, f"absent du prompt : {attendu!r}"
    assert prepared.trace["calcul_non_verifie"] is False


async def test_la_regle_du_quotient_n_est_pas_imposee_au_modele(agent_qa, session_eleve):
    """Contrôle direct du symptôme rapporté.

    La règle du quotient n'a rien à faire dans une étude de ln. On ne juge pas
    la prose — on vérifie que rien dans le prompt ne pousse le modèle vers elle,
    et que la consigne qui l'occupe est bien celle de l'étude.
    """
    prepared = await agent_qa.prepare(CAS_17.prompt, {"serie": "S2"}, session_eleve)

    assert "L'élève demande une ÉTUDE DE FONCTION" in prepared.final_prompt
    plat = prepared.final_prompt.lower()
    assert "règle du quotient" not in plat and "regle du quotient" not in plat
