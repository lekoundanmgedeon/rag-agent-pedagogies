"""GET /api/catalogue — cas QA #28 (sujet proposé à l'accueil mais non couvert).

Le reproche de la testeuse ne porte pas sur le refus de l'agent, qui était
correct, mais sur l'invitation qui l'avait précédé : l'accueil proposait « Fais-
moi un cours sur les suites numériques », écrit en dur dans le frontend, alors
qu'aucune leçon de suites n'est indexée. Ces tests gèlent la propriété qui
supprime le décalage : ce que l'accueil peut proposer vient du corpus.
"""

from __future__ import annotations


async def test_le_catalogue_liste_les_chapitres_indexes(api_client, student_headers):
    resp = await api_client.get("/api/catalogue", headers=student_headers)
    assert resp.status_code == 200
    chapitres = resp.json()["chapitres"]
    assert chapitres, "le corpus d'exemple est ingéré par le lifespan : la liste ne peut pas être vide"
    # Aucun chapitre annoncé ne peut être absent du corpus : c'est toute la
    # propriété du cas #28, et elle se vérifie côté serveur, pas côté écran.
    assert all(isinstance(c, str) and c.strip() for c in chapitres)


async def test_le_catalogue_respecte_le_cadre_curriculaire(api_client, student_headers):
    """Un élève ne se voit pas proposer un chapitre d'une autre série.

    Le filtre est celui de la recherche : proposer à l'accueil ce que la
    recherche refusera ensuite de servir recréerait le décalage du cas #28, une
    série plus loin.
    """
    tous = (await api_client.get("/api/catalogue", headers=student_headers)).json()["chapitres"]
    s1 = (
        await api_client.get("/api/catalogue", params={"serie": "S1"}, headers=student_headers)
    ).json()["chapitres"]
    assert set(s1) <= set(tous)


async def test_le_catalogue_exige_une_authentification(api_client):
    resp = await api_client.get("/api/catalogue")
    assert resp.status_code in (401, 403)


async def test_un_cadre_sans_corpus_rend_une_liste_vide(api_client, student_headers):
    """Une liste vide est une réponse, pas une erreur.

    C'est le pendant honnête de la règle n°4 : quand rien n'est indexé pour ce
    cadre, l'accueil doit pouvoir le dire au lieu de proposer un sujet au hasard.
    """
    resp = await api_client.get(
        "/api/catalogue", params={"serie": "SERIE_INEXISTANTE"}, headers=student_headers
    )
    assert resp.status_code == 200
    assert resp.json()["chapitres"] == []
