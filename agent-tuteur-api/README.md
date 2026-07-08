# agent-tuteur-api

Cœur métier + (à venir) API de l'agent tuteur pédagogique RAG pour le programme
scolaire sénégalais.

> État : **étapes 1 à 3** construites (cœur RAG + agent, exécutables hors-ligne
> en mode *mock / in-memory*). Les couches Postgres, FastAPI, ARQ/Redis,
> Streamlit et déploiement (étapes 4 à 8) ne sont pas encore présentes.

## Démo hors-ligne (sans infrastructure)

```bash
python3 -m venv .venv && source .venv/bin/activate   # ou get-pip si ensurepip absent
pip install -r requirements.txt
PYTHONPATH=src python scripts/demo.py
```

La démo exécute une ingestion du corpus d'exemple (`corpus/`) dans un vectorstore
in-memory puis pose une question à l'agent, en affichant le niveau d'indice, les
sources RAG et la réponse streamée par le LLM *mock*.

## Tests

```bash
PYTHONPATH=src python -m pytest -q
```

## Organisation du cœur (framework-agnostique)

| Module | Rôle |
|---|---|
| `config/` | réglages (`settings`) + taxonomie curriculaire (`taxonomy`) |
| `domain/` | modèles partagés (`CurriculumMetadata`, `Chunk`, `ScoredChunk`) |
| `ingestion/` | loaders, normalisation (format pivot), chunking, annotation |
| `vectorstore/` | embeddings, store (in-memory/Qdrant), indexer, retriever hybride |
| `tools/` | calculatrice symbolique SymPy en sandbox |
| `agent/` | stratégie d'indice, frustration, LLM+fallback, garde-fous, graphe LangGraph |

Voir `../architecture.md` pour la spécification complète.
