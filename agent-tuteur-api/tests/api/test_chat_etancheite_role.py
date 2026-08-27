"""Cas QA #22 — « je veux comprendre la physique » : réponse vide, et soupçon de
fuite liée au statut admin de la testeuse.

Deux moitiés, traitées séparément parce qu'elles n'ont pas la même nature.

**La réponse vide** n'est pas reproductible sur le pipeline actuel : rejoué sur
la stack Docker (2026-08-27), le tour répond honnêtement que la physique n'est
pas couverte, propose les chapitres de mathématiques disponibles et rend la main
à l'élève. Le symptôme visible côté interface — un flux qui s'arrête sans trame
``done``, indiscernable d'une génération en cours — est couvert depuis par la
conversion de toute panne en trame ``error`` (cf. ``_chat_stream``).

**L'étanchéité admin / élève** se gèle, elle, et c'est l'objet de ce fichier :
le rôle du porteur du jeton ne doit changer ni le contenu envoyé au modèle, ni
les décisions du pipeline. Le seul écart légitime est documenté dans
``_effective_student_id`` — un admin peut dialoguer *au nom d'un* élève, ce qui
change l'attribution, jamais la réponse.
"""

from __future__ import annotations

import json

QUESTION = "je veux comprendre la physique"
CONTEXTE = {"serie": "S1", "discipline": "Mathématiques"}


async def _tour(api_client, headers) -> tuple[dict, str]:
    """Un tour de chat complet : renvoie ``(meta, texte)``."""
    meta, morceaux = None, []
    async with api_client.stream(
        "POST", "/api/chat", json={"question": QUESTION, "curriculum_context": CONTEXTE},
        headers=headers,
    ) as resp:
        assert resp.status_code == 200
        async for ligne in resp.aiter_lines():
            if not ligne.startswith("data:"):
                continue
            event = json.loads(ligne[len("data:"):].strip())
            if "meta" in event:
                meta = event["meta"]
            elif "token" in event:
                morceaux.append(event["token"])
    return meta, "".join(morceaux)


async def test_la_reponse_n_est_jamais_vide(api_client, student_headers):
    """Le symptôme rapporté : un tour qui ne répond rien."""
    meta, texte = await _tour(api_client, student_headers)
    assert meta is not None
    assert texte.strip(), "le tour n'a produit aucun texte"


async def test_le_role_ne_change_pas_le_traitement(api_client, admin_headers, student_headers):
    """Étanchéité : mêmes décisions de pipeline pour un admin et pour un élève.

    On compare les décisions, pas la prose — le modèle ne répond jamais deux
    fois pareil, et c'est le pipeline qui pourrait fuir quelque chose.
    """
    meta_admin, texte_admin = await _tour(api_client, admin_headers)
    meta_eleve, texte_eleve = await _tour(api_client, student_headers)

    assert texte_admin.strip() and texte_eleve.strip()
    assert meta_admin["hint_label"] == meta_eleve["hint_label"]
    assert meta_admin["hint_level"] == meta_eleve["hint_level"]
    assert [s["label"] for s in meta_admin["sources"]] == [
        s["label"] for s in meta_eleve["sources"]
    ]
    assert [e["node"] for e in meta_admin["node_trace"]] == [
        e["node"] for e in meta_eleve["node_trace"]
    ]


async def test_aucune_information_de_role_ne_part_dans_la_trace(api_client, admin_headers):
    """Ce que le client reçoit ne doit rien dire du rôle ni du compte.

    La testeuse soupçonnait une fuite liée à son statut : le contrôle porte donc
    sur la charge réellement transmise, et pas sur une lecture du code.
    """
    meta, _ = await _tour(api_client, admin_headers)
    charge = json.dumps(meta, ensure_ascii=False).lower()
    for interdit in ("admin", "role", "password", "jwt", "bearer", "test@example.com"):
        assert interdit not in charge, f"information de compte exposée dans meta : {interdit}"
