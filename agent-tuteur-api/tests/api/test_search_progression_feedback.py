import json


async def test_search_returns_scored_chunks_from_seeded_corpus(api_client):
    resp = await api_client.post(
        "/api/search",
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


async def test_search_serie_alias_expansion(api_client):
    resp = await api_client.post(
        "/api/search",
        json={"query": "calcul de la moyenne et de l'écart-type", "curriculum_context": {"serie": "STIDD1"}},
    )
    results = resp.json()
    assert results
    assert all(r["metadata"]["serie"] == "T1" for r in results)


async def test_progression_empty_for_unknown_student(api_client, tenant_id):
    resp = await api_client.get("/api/progression/personne", headers={"X-Tenant-Id": tenant_id})
    assert resp.status_code == 200
    assert resp.json() == {"student_id": "personne", "history": [], "recurrent_difficulties": []}


async def test_feedback_roundtrip_via_chat_message(api_client, tenant_id):
    async with api_client.stream(
        "POST",
        "/api/chat",
        json={"question": "comment dériver un quotient de fonctions ?", "student_id": "eleve_fb"},
        headers={"X-Tenant-Id": tenant_id},
    ) as resp:
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[len("data:"):].strip()))
    message_id = events[-1]["done"]["message_id"]

    fb = await api_client.post(
        f"/api/messages/{message_id}/feedback",
        json={"value": 1},
        headers={"X-Tenant-Id": tenant_id},
    )
    assert fb.status_code == 200
    assert fb.json()["value"] == 1


async def test_feedback_rejects_invalid_value(api_client, tenant_id):
    resp = await api_client.post(
        "/api/messages/00000000-0000-0000-0000-000000000000/feedback",
        json={"value": 0},
        headers={"X-Tenant-Id": tenant_id},
    )
    assert resp.status_code == 422  # value hors {-1, 1} -> validation Pydantic


async def test_feedback_404_for_unknown_message(api_client, tenant_id):
    resp = await api_client.post(
        "/api/messages/00000000-0000-0000-0000-000000000000/feedback",
        json={"value": 1},
        headers={"X-Tenant-Id": tenant_id},
    )
    assert resp.status_code == 404
