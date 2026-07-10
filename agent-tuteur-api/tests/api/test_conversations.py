from tests.api.test_chat import _read_sse_events


async def _chat(api_client, tenant_id, question: str, student_id: str, conversation_id: str | None = None):
    payload = {"question": question, "student_id": student_id}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    async with api_client.stream("POST", "/api/chat", json=payload, headers={"X-Tenant-Id": tenant_id}) as resp:
        events = await _read_sse_events(resp)
    return events[-1]["done"]["conversation_id"]


async def test_conversation_titled_from_first_question(api_client, tenant_id):
    conv_id = await _chat(
        api_client, tenant_id, "comment dériver un quotient de fonctions ?", "eleve_titre"
    )
    resp = await api_client.get(
        "/api/conversations", params={"student_id": "eleve_titre"}, headers={"X-Tenant-Id": tenant_id}
    )
    assert resp.status_code == 200
    listed = resp.json()
    assert len(listed) == 1
    assert listed[0]["id"] == conv_id
    assert listed[0]["title"] == "comment dériver un quotient de fonctions ?"


async def test_conversation_list_most_recent_activity_first(api_client, tenant_id):
    conv_a = await _chat(api_client, tenant_id, "première session", "eleve_multi_conv")
    conv_b = await _chat(api_client, tenant_id, "deuxième session", "eleve_multi_conv")
    await _chat(api_client, tenant_id, "je relance la première", "eleve_multi_conv", conv_a)

    resp = await api_client.get(
        "/api/conversations", params={"student_id": "eleve_multi_conv"}, headers={"X-Tenant-Id": tenant_id}
    )
    listed = resp.json()
    assert [c["id"] for c in listed] == [conv_a, conv_b]


async def test_conversation_messages_endpoint_returns_full_history(api_client, tenant_id):
    conv_id = await _chat(api_client, tenant_id, "explique la notion de dérivée", "eleve_histo")

    resp = await api_client.get(
        f"/api/conversations/{conv_id}/messages", headers={"X-Tenant-Id": tenant_id}
    )
    assert resp.status_code == 200
    messages = resp.json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "explique la notion de dérivée"
    assert messages[1]["trace"]["hint_level"] == 1


async def test_conversation_messages_404_for_unknown_conversation(api_client, tenant_id):
    resp = await api_client.get(
        "/api/conversations/00000000-0000-0000-0000-000000000000/messages",
        headers={"X-Tenant-Id": tenant_id},
    )
    assert resp.status_code == 404


async def test_conversation_delete_removes_it_from_list(api_client, tenant_id):
    conv_id = await _chat(api_client, tenant_id, "une question à supprimer", "eleve_delete")

    resp = await api_client.delete(f"/api/conversations/{conv_id}", headers={"X-Tenant-Id": tenant_id})
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}

    listed = await api_client.get(
        "/api/conversations", params={"student_id": "eleve_delete"}, headers={"X-Tenant-Id": tenant_id}
    )
    assert listed.json() == []


async def test_conversation_delete_missing_returns_404(api_client, tenant_id):
    resp = await api_client.delete(
        "/api/conversations/00000000-0000-0000-0000-000000000000", headers={"X-Tenant-Id": tenant_id}
    )
    assert resp.status_code == 404


async def test_conversation_list_tenant_isolation(api_client, tenant_id):
    await _chat(api_client, tenant_id, "question tenant A", "eleve_iso")

    other_tenant = tenant_id + "_other"
    resp = await api_client.get(
        "/api/conversations", params={"student_id": "eleve_iso"}, headers={"X-Tenant-Id": other_tenant}
    )
    assert resp.json() == []
