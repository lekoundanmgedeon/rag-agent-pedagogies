import asyncio

MARKDOWN_DOC = (
    b"## Chapitre : Test upload API\n\n"
    b"Contenu de test pour verifier l'ingestion via l'API.\n\n"
    b"### Exercice : Test\n\n"
    b"**Enonce.** Un test.\n\n**Indice.** Un indice.\n\n**Solution.** Une solution.\n"
)


async def _wait_indexed(api_client, headers: dict, document_id: str, timeout: float = 5.0) -> dict:
    elapsed = 0.0
    while elapsed < timeout:
        resp = await api_client.get(f"/api/documents/{document_id}", headers=headers)
        data = resp.json()
        if data["status"] in {"indexed", "failed"}:
            return data
        await asyncio.sleep(0.2)
        elapsed += 0.2
    raise TimeoutError("Document jamais passé à un état terminal")


async def test_upload_ingests_and_becomes_indexed(api_client, admin_headers):
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("cours.md", MARKDOWN_DOC, "text/markdown")},
        data={"niveau": "secondaire", "discipline": "Test"},
    )
    assert resp.status_code == 200
    doc = resp.json()[0]
    assert doc["status"] == "pending"

    final = await _wait_indexed(api_client, admin_headers, doc["document_id"])
    assert final["status"] == "indexed"
    assert final["metadata"]["discipline"] == "Test"


async def test_documents_require_admin(api_client, student_headers):
    """L'espace documents est réservé aux administrateurs (403 pour un élève)."""
    resp = await api_client.get("/api/documents", headers=student_headers)
    assert resp.status_code == 403


async def test_documents_require_authentication(api_client):
    resp = await api_client.get("/api/documents")
    assert resp.status_code == 401


async def test_uploaded_document_is_searchable(api_client, admin_headers):
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("cours2.md", MARKDOWN_DOC, "text/markdown")},
    )
    doc_id = resp.json()[0]["document_id"]
    await _wait_indexed(api_client, admin_headers, doc_id)

    search = await api_client.post(
        "/api/search",
        headers=admin_headers,
        json={"query": "test upload API", "top_k": 3},
    )
    assert search.status_code == 200
    results = search.json()
    assert any(r["metadata"]["source_document"] == "cours2.md" for r in results)


async def test_list_and_delete_document(api_client, admin_headers):
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("a_supprimer.md", MARKDOWN_DOC, "text/markdown")},
    )
    doc_id = resp.json()[0]["document_id"]
    await _wait_indexed(api_client, admin_headers, doc_id)

    listing = await api_client.get("/api/documents", headers=admin_headers)
    assert any(d["id"] == doc_id for d in listing.json())

    delete = await api_client.delete(f"/api/documents/{doc_id}", headers=admin_headers)
    assert delete.status_code == 200

    get_after = await api_client.get(f"/api/documents/{doc_id}", headers=admin_headers)
    assert get_after.status_code == 404


async def test_reindex_replaces_content(api_client, admin_headers):
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("v1.md", MARKDOWN_DOC, "text/markdown")},
    )
    doc_id = resp.json()[0]["document_id"]
    await _wait_indexed(api_client, admin_headers, doc_id)

    new_content = b"## Chapitre : Contenu totalement remplace\n\nNouvelle version.\n"
    reindex = await api_client.post(
        f"/api/documents/{doc_id}/reindex",
        headers=admin_headers,
        files={"file": ("v1.md", new_content, "text/markdown")},
    )
    assert reindex.status_code == 200
    await _wait_indexed(api_client, admin_headers, doc_id)

    search = await api_client.post(
        "/api/search",
        headers=admin_headers,
        json={"query": "contenu totalement remplace", "top_k": 1},
    )
    assert "remplace" in search.json()[0]["text"].lower()


async def test_upload_rejects_unsupported_extension(api_client, admin_headers):
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("malware.exe", b"binary", "application/octet-stream")},
    )
    assert resp.status_code == 400


async def test_verify_all_marks_orphaned_document(api_client, admin_headers):
    """Reproduit le bug réel : un document "indexed" dont les vecteurs ont
    disparu du store (ex. changement de VECTOR_BACKEND, redémarrage d'un store
    en mémoire) doit être détecté et marqué "orphaned" par /verify-all."""
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("orphelin.md", MARKDOWN_DOC, "text/markdown")},
    )
    doc_id = resp.json()[0]["document_id"]
    await _wait_indexed(api_client, admin_headers, doc_id)

    # Simule la disparition des vecteurs (le statut Postgres, lui, reste "indexed").
    api_client.app.state.indexer.delete_source("orphelin.md")

    result = await api_client.post("/api/documents/verify-all", headers=admin_headers)
    assert result.status_code == 200
    body = result.json()
    assert body["checked"] >= 1
    assert any(o["document_id"] == doc_id for o in body["orphaned"])

    fetched = await api_client.get(f"/api/documents/{doc_id}", headers=admin_headers)
    assert fetched.json()["status"] == "orphaned"
    assert "ré-uploader" in fetched.json()["error"]


async def test_verify_all_leaves_consistent_documents_untouched(api_client, admin_headers):
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("sain.md", MARKDOWN_DOC, "text/markdown")},
    )
    doc_id = resp.json()[0]["document_id"]
    await _wait_indexed(api_client, admin_headers, doc_id)

    result = await api_client.post("/api/documents/verify-all", headers=admin_headers)
    assert result.json()["orphaned"] == []

    fetched = await api_client.get(f"/api/documents/{doc_id}", headers=admin_headers)
    assert fetched.json()["status"] == "indexed"


async def test_health_reports_orphaned_documents_count(api_client, admin_headers):
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("orphelin2.md", MARKDOWN_DOC, "text/markdown")},
    )
    doc_id = resp.json()[0]["document_id"]
    await _wait_indexed(api_client, admin_headers, doc_id)
    api_client.app.state.indexer.delete_source("orphelin2.md")
    await api_client.post("/api/documents/verify-all", headers=admin_headers)

    # /health est public mais renseigne le compteur d'orphelins du tenant si un
    # jeton valide est fourni.
    health = await api_client.get("/health", headers=admin_headers)
    assert health.json()["documents_orphaned"] == 1


async def test_documents_tenant_isolation(api_client, tenant_id, admin_headers, make_headers):
    resp = await api_client.post(
        "/api/documents",
        headers=admin_headers,
        files={"files": ("isole.md", MARKDOWN_DOC, "text/markdown")},
    )
    doc_id = resp.json()[0]["document_id"]

    other = make_headers(tenant_id=tenant_id + "_other", role="admin")
    listing_other = await api_client.get("/api/documents", headers=other)
    assert all(d["id"] != doc_id for d in listing_other.json())

    get_other = await api_client.get(f"/api/documents/{doc_id}", headers=other)
    assert get_other.status_code == 404
