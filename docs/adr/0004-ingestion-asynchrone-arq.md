# ADR 0004 — Ingestion asynchrone ARQ/Redis

## Contexte

L'extraction/normalisation/chunking/embedding/upsert d'un document peut prendre
plusieurs secondes (PDF volumineux, embeddings). Bloquer la requête HTTP
d'upload jusqu'à la fin de l'indexation dégraderait l'expérience et empêcherait
tout traitement par lots.

## Décision

Traitement asynchrone via une file **ARQ** (Redis) et un worker séparé
(`workers/ingestion_worker.py`), avec **repli automatique** sur
`BackgroundTasks` FastAPI (même processus) si Redis est injoignable au
démarrage de l'API.

## Justification

- ARQ s'intègre nativement à l'écosystème asyncio (cohérent avec le reste de
  la stack, contrairement à Celery qui suppose un modèle plus lourd/synchrone).
- Un worker séparé peut être mis à l'échelle indépendamment de l'API
  (`docker compose up --scale worker=3`).
- Le **même code** de pipeline (`ingestion.pipeline.process_document` +
  `vectorstore.indexer.Indexer`) est appelé par le worker ARQ et par le repli
  `BackgroundTasks` — aucune divergence de comportement entre les deux modes,
  seul l'exécuteur change. Cohérent avec le thème de dégradation gracieuse déjà
  présent pour les embeddings/vectorstore/LLM.

## Conséquences

- Un service Redis supplémentaire dans la stack.
- **Limitation multi-processus documentée** (cf. ADR 0002) : avec le
  vectorstore in-memory, le worker (processus séparé) et l'API ne partagent pas
  le même store — `VECTOR_BACKEND=qdrant` est nécessaire pour un flux
  upload→recherche cohérent dès qu'un worker séparé tourne.
- Le statut d'ingestion (`GET /api/documents/{id}/status`) est exposé par
  **sondage** de la base (500 ms) plutôt que par un flux d'événements fins
  publiés par le worker (extract/normalize/chunk/embed) — amélioration future
  possible sans changer le contrat SSE observable.
