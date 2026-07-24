"""Ingestion du corpus d'exemple via l'API (upload authentifié) — amorçage démo.

Téléverse chaque fichier de ``corpus/`` par ``POST /api/documents``, exactement
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
CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def _wait_api(timeout: float = 120.0) -> bool:
    """Poll ``/health`` jusqu'à ce que l'API réponde avec la base connectée."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{API}/health", timeout=5)
            if resp.status_code == 200 and resp.json().get("db"):
                return True
        except Exception:  # noqa: BLE001 — l'API n'est peut-être pas encore démarrée.
            pass
        time.sleep(2)
    return False


def main() -> int:
    files = sorted(CORPUS.glob("*.md")) if CORPUS.exists() else []
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
    except Exception as exc:  # noqa: BLE001 — sans admin, on n'ingère pas mais on ne bloque pas.
        print(f"Login admin échoué ({exc}) — ingestion ignorée.", file=sys.stderr)
        return 0

    headers = {"Authorization": f"Bearer {token}"}
    try:
        listed = httpx.get(f"{API}/api/documents", headers=headers, timeout=10).json()
        existing = {d["filename"] for d in listed}
    except Exception:  # noqa: BLE001 — au pire on tentera d'uploader (l'API dédoublonne par contenu).
        existing = set()

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
        except Exception as exc:  # noqa: BLE001 — on continue sur les fichiers suivants.
            print(f"  ! {path.name} : {exc}", file=sys.stderr)

    print(f"Corpus : {uploaded} document(s) téléversé(s), {len(existing)} déjà présent(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
