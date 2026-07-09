"""Client HTTP de l'API agent-tuteur — **seul** point de contact avec le backend.

Principe transversal : le frontend Streamlit ne connaît ni le cœur métier, ni la
base de données, ni le vectorstore. Toute donnée transite par ces fonctions,
qui appellent l'API FastAPI via HTTP/SSE. Aucune logique pédagogique ici.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
_TIMEOUT = 30


class ApiError(RuntimeError):
    """Erreur renvoyée par l'API (statut HTTP non 2xx)."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"[{status_code}] {detail}")
        self.status_code = status_code
        self.detail = detail


def _headers(tenant_id: str) -> dict[str, str]:
    return {"X-Tenant-Id": tenant_id}


def _raise_for_status(resp: requests.Response) -> None:
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise ApiError(resp.status_code, str(detail))


def health() -> dict:
    resp = requests.get(f"{API_BASE_URL}/health", timeout=_TIMEOUT)
    _raise_for_status(resp)
    return resp.json()


def chat_stream(
    question: str,
    student_id: str,
    tenant_id: str,
    curriculum_context: dict | None = None,
    conversation_id: str | None = None,
) -> Iterator[dict]:
    """Streame les événements SSE de ``/api/chat`` sous forme de dicts Python.

    Émet successivement des dicts ``{"meta": {...}}``, ``{"token": "..."}``,
    puis ``{"done": {...}}`` (ou ``{"error": "..."}``). Lève ``ApiError`` avant
    tout streaming si l'API rejette la requête (ex. 400 anti-injection).
    """
    payload = {
        "question": question,
        "student_id": student_id,
        "curriculum_context": curriculum_context or {},
    }
    if conversation_id:
        payload["conversation_id"] = conversation_id

    with requests.post(
        f"{API_BASE_URL}/api/chat",
        json=payload,
        headers=_headers(tenant_id),
        stream=True,
        timeout=_TIMEOUT,
    ) as resp:
        _raise_for_status(resp)
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data:
                yield json.loads(data)


def upload_documents(
    files: list[tuple[str, bytes]],
    tenant_id: str,
    metadata: dict[str, str] | None = None,
) -> list[dict]:
    """Upload un ou plusieurs fichiers. ``files`` = liste de (nom, contenu binaire)."""
    multipart = [("files", (name, content)) for name, content in files]
    resp = requests.post(
        f"{API_BASE_URL}/api/documents",
        files=multipart,
        data={k: v for k, v in (metadata or {}).items() if v},
        headers=_headers(tenant_id),
        timeout=_TIMEOUT,
    )
    _raise_for_status(resp)
    return resp.json()


def list_documents(tenant_id: str) -> list[dict]:
    resp = requests.get(f"{API_BASE_URL}/api/documents", headers=_headers(tenant_id), timeout=_TIMEOUT)
    _raise_for_status(resp)
    return resp.json()


def get_document(document_id: str, tenant_id: str) -> dict:
    resp = requests.get(
        f"{API_BASE_URL}/api/documents/{document_id}", headers=_headers(tenant_id), timeout=_TIMEOUT
    )
    _raise_for_status(resp)
    return resp.json()


def delete_document(document_id: str, tenant_id: str) -> None:
    resp = requests.delete(
        f"{API_BASE_URL}/api/documents/{document_id}", headers=_headers(tenant_id), timeout=_TIMEOUT
    )
    _raise_for_status(resp)


def reindex_document(document_id: str, tenant_id: str, filename: str, content: bytes) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/api/documents/{document_id}/reindex",
        files={"file": (filename, content)},
        headers=_headers(tenant_id),
        timeout=_TIMEOUT,
    )
    _raise_for_status(resp)
    return resp.json()


def verify_all_documents(tenant_id: str) -> dict:
    """Vérifie les documents ``indexed`` contre le vectorstore réel — marque
    ``orphaned`` ceux dont les chunks ont disparu (ex. après un changement de
    VECTOR_BACKEND). Renvoie ``{checked: int, orphaned: [...]}``."""
    resp = requests.post(
        f"{API_BASE_URL}/api/documents/verify-all", headers=_headers(tenant_id), timeout=_TIMEOUT
    )
    _raise_for_status(resp)
    return resp.json()


def search(
    query: str, tenant_id: str, curriculum_context: dict | None = None, top_k: int = 5
) -> list[dict]:
    resp = requests.post(
        f"{API_BASE_URL}/api/search",
        json={"query": query, "curriculum_context": curriculum_context or {}, "top_k": top_k},
        headers=_headers(tenant_id),
        timeout=_TIMEOUT,
    )
    _raise_for_status(resp)
    return resp.json()


def get_progression(student_id: str, tenant_id: str) -> dict:
    resp = requests.get(
        f"{API_BASE_URL}/api/progression/{student_id}", headers=_headers(tenant_id), timeout=_TIMEOUT
    )
    _raise_for_status(resp)
    return resp.json()


def submit_feedback(message_id: str, tenant_id: str, value: int) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/api/messages/{message_id}/feedback",
        json={"value": value},
        headers=_headers(tenant_id),
        timeout=_TIMEOUT,
    )
    _raise_for_status(resp)
    return resp.json()


def get_chat_logs(tenant_id: str, limit: int = 50) -> list[dict]:
    """Derniers tours de chat (tous élèves) avec leur trace complète — page Logs."""
    resp = requests.get(
        f"{API_BASE_URL}/api/logs/chat",
        params={"limit": limit},
        headers=_headers(tenant_id),
        timeout=_TIMEOUT,
    )
    _raise_for_status(resp)
    return resp.json()
