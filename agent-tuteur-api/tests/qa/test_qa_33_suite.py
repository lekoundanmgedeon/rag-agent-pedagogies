"""Cas QA #33 — « Démontre que la suite … est monotone, majorée, et calcule sa
limite » (Pierre Ndong).

Particularité du cas : le testeur **valide** la réponse. Il ne rapporte pas une
erreur, il rapporte un risque — « le besoin d'un outil de vérification pour
garantir que le raisonnement détaillé ne contient pas d'erreur cachée ». Une
démonstration par récurrence est longue, et chacune de ses étapes est une
occasion de se tromper avec assurance : c'est la situation même que vise la
règle non-négociable n°2.

Le correctif ne juge pas le raisonnement — aucun outil ne le fait ici. Il fixe
les **faits** sur lesquels ce raisonnement doit tomber (premiers termes, forme
close, monotonie, borne, limite), les déclare vérifiés et interdit de les
recalculer. Une démonstration qui conclurait autrement se contredirait alors
visiblement, sous les yeux de l'élève.
"""

from __future__ import annotations

from .cas import par_id, tous_les_cas

CAS_33 = par_id(tous_les_cas())[33]


async def test_les_faits_de_la_suite_sont_etablis(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_33.prompt, {"serie": "S2"}, session_eleve)

    suite = resultat.trace["suite_recurrente"]
    assert suite is not None, "aucune vérification symbolique sur une suite récurrente"
    assert suite["premiers_termes"][:3] == ["2", "5/2", "11/4"]
    assert suite["monotonie"] == "croissante"
    assert suite["borne"] == "majorée par 3"
    assert suite["limite"] == "3"


async def test_le_prompt_interdit_de_recalculer(agent_qa, session_eleve):
    """Les valeurs partent au modèle **comme vérifiées**, pas comme suggestions."""
    resultat = await agent_qa.respond(CAS_33.prompt, {"serie": "S2"}, session_eleve)
    prompt = resultat.final_prompt
    assert "ils sont vérifiés : reprends-les tels quels, ne les recalcule pas" in prompt
    assert "u(n) = 3 - 1/2**n" in prompt
    assert "initialisation, hérédité, conclusion" in prompt


async def test_une_suite_dont_la_limite_n_est_pas_demontree_le_dit(agent_qa, session_eleve):
    """Le pendant du correctif, et il compte autant : le silence de l'outil.

    Sur une suite divergente, aucune limite n'est établie — le prompt doit alors
    l'annoncer comme non établie plutôt que de laisser le modèle en produire une.
    """
    resultat = await agent_qa.respond(
        "Démontre que la suite définie par u_0 = 5 et u_{n+1} = 3*u_n - 4 converge, "
        "et calcule sa limite.",
        {"serie": "S2"},
        session_eleve,
    )
    suite = resultat.trace["suite_recurrente"]
    assert suite is not None and suite["limite"] is None
    assert "n'a PAS pu être établie par l'outil" in resultat.final_prompt


async def test_un_tour_ordinaire_n_est_pas_touche(agent_qa, session_eleve):
    """Aucune suite dans l'énoncé : la clé reste vide, et rien ne s'ajoute au prompt."""
    resultat = await agent_qa.respond(
        "Calcule la dérivée de x^3 - 3x.", {"serie": "S2"}, session_eleve
    )
    assert resultat.trace["suite_recurrente"] is None
    assert "suite définie par récurrence" not in resultat.final_prompt
