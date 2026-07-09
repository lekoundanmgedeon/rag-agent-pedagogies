# État de reprise — Agent Tuteur Sénégal

*Dernière mise à jour : 2026-07-09. Point de reprise pour une nouvelle session
(humaine ou Claude) — pas une doc de référence finale (voir index ci-dessous).*

## Où trouver quoi (ne pas dupliquer ici)

| Besoin | Document |
|---|---|
| Vue d'ensemble, démarrage rapide | [`README.md`](../README.md) (racine) |
| Architecture, flux, frontières | [`docs/architecture.md`](architecture.md) |
| Chaque endpoint de l'API | [`docs/api.md`](api.md) |
| Décisions techniques argumentées | [`docs/RAPPORT_TECHNIQUE.md`](RAPPORT_TECHNIQUE.md) |
| **Comment lancer (Docker/local, tous modes)** | [`docs/GUIDE_LANCEMENT.md`](GUIDE_LANCEMENT.md) |
| ADR individuelles | [`docs/adr/`](adr/) |
| Import de données antérieures | [`docs/migration.md`](migration.md) |

## Ce qui est fait (étapes 1 à 8, complètes)

Cœur RAG + agent LangGraph (indice 0-4, frustration, garde-fous, fallback LLM
Mistral→Ollama→Mock) + persistance PostgreSQL (RLS) + API FastAPI (SSE) +
ingestion asynchrone ARQ + frontend Streamlit + déploiement Docker Compose +
documentation complète. Détail exhaustif : `docs/RAPPORT_TECHNIQUE.md`.

**Ajouté après la clôture initiale des 8 étapes** :
- Logging JSON structuré (`agent_tuteur/observability.py`) + trace
  d'orchestration nœud-par-nœud persistée et visible dans Streamlit (page Logs).
- Détection des documents « orphelins » : un document marqué `indexed` dont les
  vecteurs ont disparu du vectorstore (ex. après un changement de
  `VECTOR_BACKEND`) est maintenant détecté (`POST /api/documents/verify-all` +
  vérification automatique au démarrage) et marqué `orphaned` plutôt que de
  rester silencieusement introuvable.

## ⚠️ Travail non commité à ce jour

```
M  agent-tuteur-api/src/agent_tuteur/api/main.py
M  agent-tuteur-api/src/agent_tuteur/api/routes/documents.py
M  agent-tuteur-api/src/agent_tuteur/api/routes/health.py
M  agent-tuteur-api/src/agent_tuteur/api/schemas.py
M  agent-tuteur-api/src/agent_tuteur/persistence/repositories.py
M  agent-tuteur-api/src/agent_tuteur/vectorstore/{indexer,qdrant_store,store}.py
M  agent-tuteur-api/tests/... (nouveaux tests inclus)
M  agent-tuteur-frontend/... (pages Upload/Logs, streamlit_app.py, api_client.py)
?? agent-tuteur-api/src/agent_tuteur/ingestion/consistency.py   (nouveau fichier)
?? agent-tuteur-api/tests/test_consistency.py                    (nouveau fichier)
```

C'est l'intégralité de la fonctionnalité « détection des documents orphelins »
ci-dessus. **Pas commité automatiquement** (jamais sans demande explicite) —
à committer toi-même, ou demande-le en début de prochaine session.

## État de l'environnement (au moment de la pause)

- **`.venv`** : reconstruit proprement depuis `/usr/bin/python3.12` (le
  précédent était corrompu par une incohérence avec un environnement conda —
  voir `docs/GUIDE_LANCEMENT.md` §10 si le symptôme revient : segfault sur
  `make api`/`worker`/`run`).
- **Conteneurs Docker actifs** (jetables, à toi de les arrêter si tu ne
  continues pas dans l'immédiat) :
  `tutor-pg` (55432), `tutor-redis` (56379), `qdrant` (6333).
- **`.env`** (`agent-tuteur-api/.env`, non commité) : `VECTOR_BACKEND=qdrant`,
  `LLM_BACKEND=auto`, clé Mistral renseignée. Cohérent avec l'infra ci-dessus.
- **4 documents marqués `orphaned`** dans ce Postgres de dev (dont 3 vrais
  fichiers de programme scolaire) — normal et attendu : ce sont les documents
  dont les vecteurs ont été perdus lors des changements de `VECTOR_BACKEND` en
  cours de session. **À ré-uploader** via la page Upload si tu veux les
  retrouver en recherche (le fichier original n'est pas conservé côté serveur,
  cf. `docs/adr/` sur l'absence de stockage d'objets).

## Reprendre rapidement

```bash
cd /home/aimssn/nuru/rag-agent-pedagogie
docker ps --format "{{.Names}}: {{.Ports}}"   # vérifier que tutor-pg/redis/qdrant tournent encore
make dev                                        # api + worker + frontend
```

Si les conteneurs ne tournent plus, voir `docs/GUIDE_LANCEMENT.md` §4 (mode B —
infra Docker + code local, le mode utilisé tout au long de cette session).

## Pièges déjà rencontrés cette session (évite de les re-découvrir)

1. `EMBEDDING_BACKEND=bg_m3` (typo) → `ValidationError` Pydantic, app ne démarre
   pas du tout. Valeur correcte : `bge_m3`.
2. `VECTOR_BACKEND=qdrant` sans Qdrant lancé → l'API plante au démarrage (pas
   de repli gracieux, contrairement à Redis).
3. `make worker` sans Redis lancé → échec attendu (ARQ a besoin de Redis pour
   démarrer, aucun mode dégradé pour le worker lui-même).
4. Séries `"S"`/`"LS"` (au lieu de `S1`-`S5`/`L1a`-`LA` etc.) ne matchent aucun
   alias de la taxonomie — le filtrage RAG par série échoue silencieusement.
5. Changer `VECTOR_BACKEND` en cours de route (memory ↔ qdrant) rend les
   documents déjà « indexed » orphelins — c'est précisément ce que la nouvelle
   détection (`verify-all` + check au démarrage) signale désormais.
