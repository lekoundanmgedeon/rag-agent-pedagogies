"""Fournisseur Gemini et chaîne de repli configurable (module 6 de la fusion).

Aucun appel réseau réel : les réponses HTTP sont simulées avec le transport de
test d'``httpx``. On vérifie ce que le code fait de la réponse, pas ce que
Google renvoie.
"""

import json

import httpx
import pytest

from agent_tuteur.agent.llm.base import LLMError
from agent_tuteur.agent.llm.gemini import GeminiLLM, _extraire_texte, _parse_ligne_sse
from agent_tuteur.agent.llm.router import build_router


def _reponse_gemini(texte: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": texte}]}}]}


# --- Lecture d'une réponse ----------------------------------------------------


def test_le_texte_est_extrait_d_une_reponse_normale():
    assert _extraire_texte(_reponse_gemini("La dérivée est $2x$.")) == "La dérivée est $2x$."


def test_les_fragments_multiples_sont_recolles():
    data = {"candidates": [{"content": {"parts": [{"text": "La "}, {"text": "dérivée."}]}}]}
    assert _extraire_texte(data) == "La dérivée."


def test_une_reponse_bloquee_par_le_filtre_bascule_vers_le_suivant():
    """Google renvoie 200 sans candidat quand son filtre de sécurité a coupé.

    Ce n'est pas une réponse vide à montrer à l'élève : c'est une erreur, pour
    que la chaîne de repli essaie le fournisseur suivant.
    """
    with pytest.raises(LLMError, match="SAFETY"):
        _extraire_texte({"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}})


def test_une_reponse_sans_candidat_est_une_erreur():
    with pytest.raises(LLMError):
        _extraire_texte({})


def test_une_reponse_vide_est_une_erreur():
    with pytest.raises(LLMError):
        _extraire_texte({"candidates": [{"content": {"parts": [{"text": ""}]}}]})


# --- Lecture du flux ----------------------------------------------------------


def test_un_fragment_de_flux_est_lu():
    ligne = "data: " + json.dumps(_reponse_gemini("bonjour"))
    assert _parse_ligne_sse(ligne) == "bonjour"


@pytest.mark.parametrize(
    "ligne",
    ["", "   ", "event: ping", "data:", "data: pas-du-json", "data: {}"],
)
def test_le_bruit_de_protocole_est_ignore_sans_erreur(ligne):
    assert _parse_ligne_sse(ligne) is None


# --- Appels HTTP (simulés) ----------------------------------------------------


@pytest.fixture
def gemini_qui_repond(monkeypatch):
    """Remplace le client HTTP par un transport simulé renvoyant une réponse fixe."""

    def _installer(handler):
        vrai_client = httpx.AsyncClient

        def _client(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            return vrai_client(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", _client)

    return _installer


async def test_generate_renvoie_le_texte(gemini_qui_repond):
    gemini_qui_repond(
        lambda requete: httpx.Response(200, json=_reponse_gemini("La dérivée est $2x$."))
    )
    assert await GeminiLLM("test-key").generate("q") == "La dérivée est $2x$."


async def test_la_consigne_systeme_n_est_pas_un_message_de_l_eleve(gemini_qui_repond):
    """Chez Gemini elle a son propre champ ; la mettre dans `contents` la
    ferait passer pour une réplique de l'élève."""
    corps = {}

    def _handler(requete):
        corps.update(json.loads(requete.content))
        return httpx.Response(200, json=_reponse_gemini("ok"))

    gemini_qui_repond(_handler)
    await GeminiLLM("test-key").generate("q", system="Tu es un tuteur.")

    assert corps["systemInstruction"]["parts"][0]["text"] == "Tu es un tuteur."
    assert len(corps["contents"]) == 1


async def test_une_erreur_http_devient_une_erreur_de_modele(gemini_qui_repond):
    """Condition du repli : toute panne doit être une LLMError, pas une httpx."""
    gemini_qui_repond(lambda requete: httpx.Response(429, json={"error": "quota"}))
    with pytest.raises(LLMError, match="Gemini"):
        await GeminiLLM("test-key").generate("q")


async def test_sans_cle_l_appel_echoue_proprement():
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        await GeminiLLM("").generate("q")


def test_le_fournisseur_se_declare_indisponible_sans_cle():
    assert GeminiLLM("").available() is False
    assert GeminiLLM("test-key").available() is True


async def test_le_flux_est_restitue_fragment_par_fragment(gemini_qui_repond):
    corps = "\n".join(
        "data: " + json.dumps(_reponse_gemini(mot)) for mot in ["La ", "dérivée ", "est $2x$."]
    )
    gemini_qui_repond(lambda requete: httpx.Response(200, text=corps))

    fragments = [f async for f in GeminiLLM("test-key").generate_stream("q")]
    assert "".join(fragments) == "La dérivée est $2x$."


# --- Composition de la chaîne -------------------------------------------------


def test_la_chaine_explicite_impose_l_ordre():
    """Le point Q2 de la synthèse : changer de fournisseur sans toucher au code."""
    routeur = build_router(chain="gemini,mistral", gemini_api_key="g", mistral_api_key="m")
    assert routeur.chain == ["gemini", "mistral", "mock"]


def test_le_mock_ferme_toujours_la_marche():
    """Même oublié dans le .env : sans lui, une panne générale laisse l'élève sans réponse."""
    assert build_router(chain="gemini").chain == ["gemini", "mock"]


def test_un_nom_inconnu_est_ignore_sans_faire_echouer_le_demarrage():
    """Une faute de frappe dans un .env ne doit pas empêcher le service de répondre."""
    routeur = build_router(chain="gemini,gpt4,mistral")
    assert routeur.chain == ["gemini", "mistral", "mock"]


def test_la_chaine_explicite_l_emporte_sur_le_backend():
    routeur = build_router(backend="mistral", chain="gemini,mock", gemini_api_key="g")
    assert routeur.chain == ["gemini", "mock"]


def test_gemini_est_selectionnable_comme_backend_unique():
    assert build_router(backend="gemini", gemini_api_key="g").chain == ["gemini", "mock"]


def test_en_mode_auto_gemini_prend_le_relais_sans_cle_mistral():
    routeur = build_router(backend="auto", gemini_api_key="g", probe_ollama=False)
    assert routeur.chain == ["gemini", "ollama", "mock"]


def test_en_mode_auto_les_deux_cles_composent_une_chaine_complete():
    routeur = build_router(
        backend="auto", mistral_api_key="m", gemini_api_key="g", probe_ollama=False
    )
    assert routeur.chain == ["mistral", "gemini", "ollama", "mock"]


def test_sans_aucune_cle_seul_le_mock_reste():
    assert build_router(backend="auto", probe_ollama=False).chain == ["mock"]


def test_le_comportement_historique_sans_gemini_est_inchange():
    """Non-régression : une configuration existante doit donner la même chaîne."""
    routeur = build_router(backend="auto", mistral_api_key="m", probe_ollama=False)
    assert routeur.chain == ["mistral", "ollama", "mock"]
