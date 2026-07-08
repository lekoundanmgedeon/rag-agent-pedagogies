# ADR 0002 — Qdrant + PostgreSQL (plutôt que pgvector consolidé)

## Contexte

Le RAG a besoin d'une recherche vectorielle **hybride** (dense + sparse, fusion
RRF) filtrée par métadonnées curriculaires. Une alternative aurait été de tout
consolider dans PostgreSQL via l'extension `pgvector`.

## Décision

Qdrant dédié pour les vecteurs, PostgreSQL dédié pour le relationnel — deux
stores séparés plutôt qu'un `pgvector` unique.

## Justification

- Qdrant a un support natif du **filtrage par payload combiné à la recherche
  vectorielle** avec index dédiés, et une fusion RRF native (dense + sparse)
  côté serveur — `pgvector` demande plus de travail applicatif pour un résultat
  hybride équivalent (sparse vectors moins natifs, RRF à recoder).
- Séparation des responsabilités : le contenu curriculaire (Qdrant) a un cycle
  de vie et des besoins de scalabilité différents des données transactionnelles
  élève (Postgres) — les tenants/écoles n'ont pas forcément le même volume de
  corpus que d'interactions.
- Dégradation gracieuse : un store in-memory (même interface `BaseVectorStore`)
  permet de tourner sans serveur Qdrant en dev/tests, ce qui aurait été moins
  naturel avec une dépendance `pgvector` figée dans le même Postgres que les
  données transactionnelles.

## Conséquences

- Un service supplémentaire (Qdrant) dans la stack.
- **Limitation documentée** : avec le backend in-memory (dev hors-ligne),
  chaque processus (API, worker ARQ) a son propre store — un document ingéré
  par le worker n'est visible en recherche que si les deux processus partagent
  Qdrant (configuration recommandée dès qu'un worker séparé est utilisé, cf.
  `docker-compose.dev.yml`).
- Deux systèmes à sauvegarder/superviser au lieu d'un seul (cf. `scripts/backup.sh`).
