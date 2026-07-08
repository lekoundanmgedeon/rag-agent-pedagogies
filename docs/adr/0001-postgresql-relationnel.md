# ADR 0001 — PostgreSQL pour le relationnel

## Contexte

L'agent a besoin de stocker des données structurées, transactionnelles et
interrogeables par agrégation : mémoire élève (`progress`), audit pédagogique
(`audit_log`), conversations/messages, feedback, métadonnées de documents.

## Décision

PostgreSQL (via SQLAlchemy async + asyncpg), plutôt qu'une base NoSQL ou un
stockage dans le vectorstore.

## Justification

- Transactions ACID nécessaires pour la cohérence conversation/message/feedback.
- Requêtes d'agrégation natives (`GROUP BY`, `COUNT`) pour les difficultés
  récurrentes (`ProgressRepository.recurrent_difficulties`).
- Row Level Security natif (cf. ADR 0006) pour l'isolation multi-tenant en
  défense en profondeur.
- Écosystème mature (Alembic pour les migrations, SQLAlchemy 2.0 async).

## Conséquences

- Un service Postgres supplémentaire dans la stack (déjà nécessaire vu la
  stack verrouillée).
- Les repositories (`persistence/repositories.py`) traduisent les ports du
  cœur agent (`StudentMemoryPort`, `AuditLogPort`) en requêtes SQL — le cœur
  métier ignore l'existence de Postgres.
