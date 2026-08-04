"""Exporte le schéma OpenAPI de l'API dans un fichier JSON.

Ce schéma est le **contrat** entre l'API et le frontend : c'est lui qui sert à
générer les types TypeScript côté navigateur.

```bash
python scripts/export_openapi.py                    # -> openapi.json
python scripts/export_openapi.py docs/openapi.json  # ailleurs

# puis, côté frontend :
npx openapi-typescript openapi.json -o src/types/api.d.ts
```

L'intérêt de générer les types plutôt que de les écrire à la main : renommer un
champ côté API casse alors la compilation du frontend, au lieu de produire un
``undefined`` silencieux une fois en production. C'est le mécanisme qui empêche
les deux moitiés du projet de re-diverger.

Aucun service n'est nécessaire (ni base, ni Qdrant, ni modèle) : le schéma se
déduit des routes et des modèles Pydantic.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DESTINATION_PAR_DEFAUT = Path("openapi.json")


def main() -> int:
    # Backends inertes : on ne veut construire que la description des routes.
    os.environ.setdefault("VECTOR_BACKEND", "memory")
    os.environ.setdefault("LLM_BACKEND", "mock")

    from agent_tuteur.api.main import create_app

    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINATION_PAR_DEFAUT
    schema = create_app().openapi()

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Schéma OpenAPI écrit dans {destination} ({len(schema.get('paths', {}))} chemins).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
