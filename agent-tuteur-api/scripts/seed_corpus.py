<<<<<<< HEAD
"""Ingestion des documents via l'API (upload authentifié) — amorçage démo.

Téléverse chaque fichier de ``corpus/`` ou du dossier configuré par
``CORPUS_DIR`` par ``POST /api/documents``, exactement
=======
"""Ingestion du corpus d'exemple via l'API (upload authentifié) — amorçage démo.

Téléverse chaque fichier de ``corpus/`` par ``POST /api/documents``, exactement
>>>>>>> 12555b75fe53161ddcede17d5663bb2b1f1155a8
comme le ferait un administrateur depuis l'interface : cela crée à la fois les
entrées ``Document`` (visibles dans l'espace admin) **et** les vecteurs
(recherche/chat), en passant par la vraie pipeline d'ingestion (frontmatter,
chunking, annotation). Idempotent : saute les fichiers déjà présents.

Conçu pour tourner comme service one-shot du docker-compose de dev, après la
création du compte admin. Attend que l'API soit prête avant d'agir ; ne fait
jamais échouer le démarrage de la stack (sort en 0 même en cas de souci).

    API_BASE_URL=http://api:8000 SEED_ADMIN_EMAIL=... SEED_ADMIN_PASSWORD=... \
        python scripts/seed_corpus.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx

API = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "admin@tuteur.sn")
PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "changeme123")
<<<<<<< HEAD
CORPUS = Path(os.environ.get("CORPUS_DIR", Path(__file__).resolve().parents[1] / "corpus"))
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


def _content_type(path: Path) -> str:
    """Return the MIME type expected by the upload endpoint."""
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
    }[path.suffix.lower()]
=======
CORPUS = Path(__file__).resolve().parents[1] / "corpus"
>>>>>>> 12555b75fe53161ddcede17d5663bb2b1f1155a8


def _wait_api(timeout: float = 120.0) -> bool:
    """Poll ``/health`` jusqu'à ce que l'API réponde avec la base connectée."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{API}/health", timeout=5)
            if resp.status_code == 200 and resp.json().get("db"):
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def main() -> int:
<<<<<<< HEAD
    files = sorted(
        path for path in CORPUS.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ) if CORPUS.exists() else []
=======
    files = sorted(CORPUS.glob("*.md")) if CORPUS.exists() else []
>>>>>>> 12555b75fe53161ddcede17d5663bb2b1f1155a8
    if not files:
        print(f"Aucun corpus à ingérer ({CORPUS}).")
        return 0

    if not _wait_api():
        print("API indisponible — ingestion du corpus ignorée.", file=sys.stderr)
        return 0

    try:
        resp = httpx.post(
            f"{API}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=10
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
    except Exception as exc:
        print(f"Login admin échoué ({exc}) — ingestion ignorée.", file=sys.stderr)
        return 0

    headers = {"Authorization": f"Bearer {token}"}
    try:
        listed = httpx.get(f"{API}/api/documents", headers=headers, timeout=10).json()
        existing = {d["filename"] for d in listed}
    except Exception:
        existing = set()

<<<<<<< HEAD
    pending = [path for path in files if path.name not in existing]
    uploaded = 0
    batches = [pending[start : start + 5] for start in range(0, len(pending), 5)]
    while batches:
        batch = batches.pop(0)
        files_payload = [
            ("files", (path.name, path.read_bytes(), _content_type(path)))
            for path in batch
        ]
        for attempt in range(12):
            try:
                resp = httpx.post(
                    f"{API}/api/documents",
                    headers=headers,
                    files=files_payload,
                    timeout=300,
                )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", "7"))
                    print(f"  ~ Limitation de débit, attente {retry_after:.0f}s...", file=sys.stderr)
                    time.sleep(max(retry_after, 1))
                    continue
                if resp.status_code == 413 and len(batch) > 1:
                    midpoint = max(len(batch) // 2, 1)
                    batches[0:0] = [batch[:midpoint], batch[midpoint:]]
                    print(f"  ~ Lot trop volumineux, découpage de {len(batch)} fichier(s).", file=sys.stderr)
                    break
                resp.raise_for_status()
                uploaded += len(batch)
                existing.update(path.name for path in batch)
                for path in batch:
                    print(f"  + {path.name}")
                break
            except Exception as exc:
                print(f"  ! Lot {[path.name for path in batch]} : {exc}", file=sys.stderr)
                break
=======
    uploaded = 0
    for path in files:
        if path.name in existing:
            continue
        try:
            resp = httpx.post(
                f"{API}/api/documents",
                headers=headers,
                files={"files": (path.name, path.read_bytes(), "text/markdown")},
                timeout=30,
            )
            resp.raise_for_status()
            uploaded += 1
            print(f"  + {path.name}")
        except Exception as exc:
            print(f"  ! {path.name} : {exc}", file=sys.stderr)
>>>>>>> 12555b75fe53161ddcede17d5663bb2b1f1155a8

    print(f"Corpus : {uploaded} document(s) téléversé(s), {len(existing)} déjà présent(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
