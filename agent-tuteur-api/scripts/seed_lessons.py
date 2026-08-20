import os
import time
from pathlib import Path

import httpx

API_URL = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@tuteur.sn")
PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "changeme123")
LESSONS_DIR = Path(os.getenv("LESSONS_DIR", "/app/lessons"))


def wait_for_api():
    for _ in range(60):
        try:
            response = httpx.get(f"{API_URL}/health", timeout=5)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)

    raise RuntimeError("API indisponible")


def main():
    files = sorted(LESSONS_DIR.rglob("*.pdf"))

    if not files:
        raise RuntimeError(f"Aucun PDF trouvé dans {LESSONS_DIR}")

    wait_for_api()

    response = httpx.post(
        f"{API_URL}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=20,
    )
    response.raise_for_status()

    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    uploaded = 0

    for file_path in files:
        print(f"Ingestion : {file_path.name}")

        with file_path.open("rb") as file:
            response = httpx.post(
                f"{API_URL}/api/documents",
                headers=headers,
                files={
                    "files": (
                        file_path.name,
                        file,
                        "application/pdf",
                    )
                },
                timeout=120,
            )

        if response.status_code in (200, 201, 202):
            uploaded += 1
            print(f"OK : {file_path.name}")
        else:
            print(f"ERREUR {response.status_code} : {file_path.name}")
            print(response.text)

    print(f"\n{uploaded}/{len(files)} fichiers envoyés.")


if __name__ == "__main__":
    main()