from tests.api.test_chat import _read_sse_events


async def _chat(api_client, headers, question: str, student_id: str, conversation_id: str | None = None):
    payload = {"question": question, "student_id": student_id}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    async with api_client.stream("POST", "/api/chat", json=payload, headers=headers) as resp:
        events = await _read_sse_events(resp)
    return events[-1]["done"]["conversation_id"]


async def test_conversation_titled_from_first_question(api_client, admin_headers):
    conv_id = await _chat(
        api_client, admin_headers, "comment dériver un quotient de fonctions ?", "eleve_titre"
    )
    resp = await api_client.get(
        "/api/conversations", params={"student_id": "eleve_titre"}, headers=admin_headers
    )
    assert resp.status_code == 200
    listed = resp.json()
    assert len(listed) == 1
    assert listed[0]["id"] == conv_id
    assert listed[0]["title"] == "comment dériver un quotient de fonctions ?"


async def test_conversation_list_most_recent_activity_first(api_client, admin_headers):
    conv_a = await _chat(api_client, admin_headers, "première session", "eleve_multi_conv")
    conv_b = await _chat(api_client, admin_headers, "deuxième session", "eleve_multi_conv")
    await _chat(api_client, admin_headers, "je relance la première", "eleve_multi_conv", conv_a)

    resp = await api_client.get(
        "/api/conversations", params={"student_id": "eleve_multi_conv"}, headers=admin_headers
    )
    listed = resp.json()
    assert [c["id"] for c in listed] == [conv_a, conv_b]


async def test_conversation_messages_endpoint_returns_full_history(api_client, admin_headers):
    # Question socratique (mode exercice) : la trace porte un hint_level. Une
    # demande de cours ("explique la notion de …") route en mode cours où
    # hint_level est None — testé ailleurs (cf. mode cours didactique).
    question = "comment dériver un quotient de fonctions ?"
    conv_id = await _chat(api_client, admin_headers, question, "eleve_histo")

    resp = await api_client.get(f"/api/conversations/{conv_id}/messages", headers=admin_headers)
    assert resp.status_code == 200
    messages = resp.json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == question
    assert messages[1]["trace"]["hint_level"] == 1


async def test_conversation_messages_404_for_unknown_conversation(api_client, admin_headers):
    resp = await api_client.get(
        "/api/conversations/00000000-0000-0000-0000-000000000000/messages",
        headers=admin_headers,
    )
    assert resp.status_code == 404


async def test_conversation_delete_removes_it_from_list(api_client, admin_headers):
    conv_id = await _chat(api_client, admin_headers, "une question à supprimer", "eleve_delete")

    resp = await api_client.delete(f"/api/conversations/{conv_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}

    listed = await api_client.get(
        "/api/conversations", params={"student_id": "eleve_delete"}, headers=admin_headers
    )
    assert listed.json() == []


async def test_conversation_delete_missing_returns_404(api_client, admin_headers):
    resp = await api_client.delete(
        "/api/conversations/00000000-0000-0000-0000-000000000000", headers=admin_headers
    )
    assert resp.status_code == 404


async def test_conversation_student_cannot_read_another_students(api_client, tenant_id, make_headers):
    """Un élève ne peut pas ouvrir la conversation d'un autre élève (404, pas de fuite)."""
    admin = make_headers(tenant_id=tenant_id, role="admin")
    conv_id = await _chat(api_client, admin, "conversation privée", "eleve_a")

    intrus = make_headers(tenant_id=tenant_id, role="student", student_id="eleve_b")
    resp = await api_client.get(f"/api/conversations/{conv_id}/messages", headers=intrus)
    assert resp.status_code == 404


async def test_conversation_list_tenant_isolation(api_client, tenant_id, admin_headers, make_headers):
    await _chat(api_client, admin_headers, "question tenant A", "eleve_iso")

    other = make_headers(tenant_id=tenant_id + "_other", role="admin")
    resp = await api_client.get("/api/conversations", params={"student_id": "eleve_iso"}, headers=other)
    assert resp.json() == []
