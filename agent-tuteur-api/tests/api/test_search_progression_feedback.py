import json


async def test_search_returns_scored_chunks_from_seeded_corpus(api_client, admin_headers):
    resp = await api_client.post(
        "/api/search",
        headers=admin_headers,
        json={
            "query": "comment dériver un quotient de fonctions",
            "curriculum_context": {"serie": "S1", "discipline": "Mathématiques"},
            "top_k": 3,
        },
    )
    assert resp.status_code == 200
    results = resp.json()
    assert results
    assert results[0]["metadata"]["source_document"] == "maths_ts1_derivees.md"
    assert results[0]["score"] > 0


async def test_search_requires_admin(api_client, student_headers):
    resp = await api_client.post(
        "/api/search", headers=student_headers, json={"query": "quoi que ce soit"}
    )
    assert resp.status_code == 403


async def test_search_serie_alias_expansion(api_client, admin_headers):
    resp = await api_client.post(
        "/api/search",
        headers=admin_headers,
        json={"query": "calcul de la moyenne et de l'écart-type", "curriculum_context": {"serie": "STIDD1"}},
    )
    results = resp.json()
    assert results
    assert all(r["metadata"]["serie"] == "T1" for r in results)


async def test_progression_empty_for_unknown_student(api_client, admin_headers):
    resp = await api_client.get("/api/progression/personne", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"student_id": "personne", "history": [], "recurrent_difficulties": []}


async def test_progression_student_cannot_read_another(api_client, tenant_id, make_headers):
    """Un élève ne peut consulter que sa propre progression (403 sinon)."""
    headers = make_headers(tenant_id=tenant_id, role="student", student_id="eleve_moi")
    resp = await api_client.get("/api/progression/quelqun_dautre", headers=headers)
    assert resp.status_code == 403


async def test_feedback_roundtrip_via_chat_message(api_client, admin_headers):
    async with api_client.stream(
        "POST",
        "/api/chat",
        json={"question": "comment dériver un quotient de fonctions ?", "student_id": "eleve_fb"},
        headers=admin_headers,
    ) as resp:
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[len("data:"):].strip()))
    message_id = events[-1]["done"]["message_id"]

    fb = await api_client.post(
        f"/api/messages/{message_id}/feedback",
        json={"value": 1},
        headers=admin_headers,
    )
    assert fb.status_code == 200
    assert fb.json()["value"] == 1


async def test_feedback_rejects_invalid_value(api_client, admin_headers):
    resp = await api_client.post(
        "/api/messages/00000000-0000-0000-0000-000000000000/feedback",
        json={"value": 0},
        headers=admin_headers,
    )
    assert resp.status_code == 422  # value hors {-1, 1} -> validation Pydantic


async def test_feedback_404_for_unknown_message(api_client, admin_headers):
    resp = await api_client.post(
        "/api/messages/00000000-0000-0000-0000-000000000000/feedback",
        json={"value": 1},
        headers=admin_headers,
    )
    assert resp.status_code == 404
