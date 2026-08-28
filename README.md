# Agent Tuteur Sénégal

Agent tuteur pédagogique **RAG + outils** pour le programme scolaire
sénégalais (préscolaire → Baccalauréat), à posture **socratique** : l'agent
guide l'élève vers la réponse par des indices progressifs plutôt que de la
donner directement, s'appuie sur un corpus curriculaire officiel filtré par
taxonomie (niveau/série/discipline), et sait déléguer le calcul à un outil
symbolique.

## Structure du dépôt

```
agent-tuteur-api/       Cœur métier + API FastAPI + worker ARQ
agent-tuteur-web/       Frontend Vue 3 + Vite — interface unique (élève + administration)
agent-tuteur-deploy/    docker-compose (dev/prod), nginx, scripts
docs/                   STATUS.md, architecture.md, api.md, adr/, guides
.github/workflows/      Intégration continue (5 vérifications par proposition)
JOURNAL_FUSION.md       Journal de la fusion NURU × ATS, module par module
REPRISE_FUSION.md       Historique d'avancement de la fusion (archive)
```

👉 **Pour reprendre le travail, lire [`docs/STATUS.md`](docs/STATUS.md)** : état
vérifié, commandes, ce qu'il reste à décider, pièges déjà rencontrés.

## Architecture (résumé)

Le **cœur métier** (`agent/`, `vectorstore/`, `ingestion/`, `tools/`,
`config/`, `domain/`, sous `agent-tuteur-api/src/agent_tuteur/`) ne dépend
d'aucun framework web ni de base de données — il est testable et exécutable
hors-ligne (LLM mock, vectorstore in-memory). `api/` (FastAPI), `workers/`
(ARQ) et `persistence/` (PostgreSQL) sont aux extrémités et consomment ce
cœur. Le frontend (Vue 3, espaces élève + administration) ne parle qu'HTTP/SSE
à l'API, authentifié par jeton JWT (rôles `admin`, `teacher`, `parent`, `student`).
Le schéma OpenAPI reste versionné : c'est le contrat publié de l'API, vérifié à
chaque proposition de modification.

L'agent tient **trois postures** : *exercice* (indices socratiques gradués,
posture par défaut), *cours* (exposé section par section) et *quiz*
(évaluation). Le suivi de la maîtrise, compétence par compétence, alimente
badges et recommandations.

## Documentation

| Besoin | Document |
|---|---|
| **Reprendre le travail** — état vérifié, ce qu'il reste à décider | [`docs/STATUS.md`](docs/STATUS.md) |
| **Lancer le projet** — tous les modes, dépannage | [`docs/GUIDE_LANCEMENT.md`](docs/GUIDE_LANCEMENT.md) |
| Architecture : composants, flux, frontières, domaine pédagogique | [`docs/architecture.md`](docs/architecture.md) |
| Chaque endpoint (requête / réponse / SSE) | [`docs/api.md`](docs/api.md) |
| Pourquoi ce choix technique — alternatives écartées | [`docs/RAPPORT_TECHNIQUE.md`](docs/RAPPORT_TECHNIQUE.md) |
| Décisions d'architecture, dont la fusion | [`docs/adr/`](docs/adr/) — [ADR 0010](docs/adr/0010-fusion-nuru-ats.md) |
| Résultat de la fusion NURU × ATS, pour la réunion | [`docs/RAPPORT_FUSION.md`](docs/RAPPORT_FUSION.md) |
| Détail de la fusion, module par module | [`JOURNAL_FUSION.md`](JOURNAL_FUSION.md) |
| Import de données antérieures | [`docs/migration.md`](docs/migration.md) |
| Mise en ligne sur un VPS d'équipe | [`docs/DEPLOIEMENT_TEST.md`](docs/DEPLOIEMENT_TEST.md) |

Les documents `COMPARATIF_ARCHITECTURES.md`, `SYNTHESE_REUNION_TECHNIQUE.md` et
`ARCHITECTURE_CIBLE.md` décrivent le projet **tel qu'il était prévu** avant la
fusion. Ce sont des archives : elles portent un bandeau et ne sont plus mises à
jour.

## ⚠️ Après toute modification d'une route d'API

Le schéma OpenAPI est versionné : c'est le contrat publié de l'API. Le
régénérer, sinon **l'intégration continue échoue** :

```bash
cd agent-tuteur-api && python scripts/export_openapi.py openapi.json
```

Un schéma périmé est une documentation fausse : `/docs` et les intégrations
tierces décrivent alors une API qui n'existe plus.

## Prérequis

- Python 3.11+
- PostgreSQL 16, Redis 7 — et Qdrant si `VECTOR_BACKEND=qdrant` (recommandé
  dès qu'un worker d'ingestion tourne séparément de l'API, cf. limitation
  ci-dessous)
- Docker + Docker Compose (pour `agent-tuteur-deploy/`)

## Démarrage rapide — Docker Compose (recommandé)

```bash
cd agent-tuteur-deploy
docker compose -f docker-compose.dev.yml up -d --build
```

Démarre Postgres, Redis, Qdrant, applique les migrations (`migrate`), puis
lance l'API (`:8000`), le worker ARQ, et le frontend **Vue** (`:8080`).

- Frontend web : http://localhost:8080
- API : http://localhost:8000/docs
- Health check : http://localhost:8000/health

Le frontend servi par le compose est le **Vue** — c'est désormais le seul du
dépôt. Pour le lancer hors Docker, avec rechargement à chaud :

```bash
cd agent-tuteur-web
npm install && npm run dev      # http://localhost:5173, proxy /api -> :8000
```

**Créer le premier compte admin** (l'API exige une authentification ; aucun
compte par défaut) :

```bash
docker compose -f docker-compose.dev.yml --profile seed run --rm createadmin
# défaut : admin@tuteur.sn / changeme123 (ADMIN_EMAIL/ADMIN_PASSWORD surchargeables)
```

Pour la production : `docker-compose.prod.yml` (secrets via `.env.prod`, nginx
en frontal avec SSL/rate limiting, aucun port interne exposé). Voir
`agent-tuteur-deploy/scripts/setup.sh` (certificat + `.env.prod` de départ) et
`scripts/deploy.sh`.

## Démarrage local (sans Docker)

```bash
make setup      # crée .venv (API) + npm install (frontend Vue)
make migrate    # applique les migrations Alembic (DATABASE_URL requis)
make createadmin EMAIL=admin@tuteur.sn PASSWORD=changeme123   # 1er compte
make dev        # lance api + worker + frontend Vue (Vite :5173) en parallèle
```

Cibles individuelles : `make api`, `make worker`, `make run` (frontend Vite),
`make createadmin`, `make test`, `make seed` (ingère le corpus d'exemple). Voir
le `Makefile` pour le détail de chaque cible et ses prérequis. Node.js 20+ est
requis pour le frontend en local.

⚠️ **`make setup` n'installe pas l'extra `parsing`** (PyMuPDF). Sans lui, la
lecture des PDF retombe silencieusement sur `pypdf`, qui **abîme les formules**
— l'ingestion « réussit » en dégradant le contenu, et seule une ligne de journal
le signale. Sur une machine neuve, ajouter :

```bash
.venv/bin/pip install -e 'agent-tuteur-api[parsing,dev]'
```

**Démo 100% hors-ligne** (sans Postgres/Redis/Qdrant, LLM mock, vectorstore
in-memory) :

```bash
cd agent-tuteur-api
PYTHONPATH=src python scripts/demo.py
```

## Variables d'environnement

Voir `agent-tuteur-api/.env.example` (backend : DB, Redis, Qdrant, LLM,
`JWT_SECRET`, rate limiting) et `agent-tuteur-web/.env.example`
(`VITE_API_TARGET`, frontend Vue). Tous les défauts permettent un fonctionnement dégradé sans
infrastructure lourde (backends légers, LLM mock) — voir la section
« Dégradation gracieuse » de `docs/architecture.md`. En production, définir un
`JWT_SECRET` fort (≥ 32 octets).

**Choisir le modèle de langage** — `LLM_CHAIN` fixe l'ordre de la chaîne de
repli et l'emporte sur `LLM_BACKEND` :

```bash
LLM_CHAIN=gemini,mistral,mock     # valeurs : mistral, gemini, ollama, mock
```

Changer de fournisseur principal est donc un réglage de `.env`, sans
modification de code ni redéploiement. `LLM_CHAIN` vide compose la chaîne
automatiquement selon les clés disponibles (`MISTRAL_API_KEY`,
`GEMINI_API_KEY`, Ollama joignable). Le **mock est toujours le dernier
maillon** : la génération ne bloque jamais, et un élève ne reçoit jamais un
message de configuration à la place d'une réponse. `GET /health` affiche la
chaîne effective. Détail : [`docs/GUIDE_LANCEMENT.md`](docs/GUIDE_LANCEMENT.md) §6.2.

⚠️ **RLS et rôle Postgres** : en production, `DATABASE_URL` de l'API/du worker
doit utiliser un rôle **non-superuser** (`postgres-init/01-app-role.sh` dans
`agent-tuteur-deploy/`) — un superuser Postgres contourne toujours le Row
Level Security, même avec `FORCE ROW LEVEL SECURITY`.

## Formats supportés

- **Corpus curriculaire** : PDF, DOCX, TXT, MD (upload via `POST /api/documents`).
  Les PDF sont lus par **PyMuPDF**, qui préserve fractions, indices et exposants
  — `pypdf` sert de repli et les abîme (voir l'extra `parsing` plus haut).
- **Format pivot interne** : Markdown + LaTeX inline (`$...$`, `$$...$$`) — cf.
  [ADR 0007](docs/adr/0007-format-pivot-markdown-latex.md).

## Tests

```bash
cd agent-tuteur-api                # depuis ce répertoire, pas la racine du dépôt
python -m pytest -q                # 317 passés, 98 ignorés
ruff check .                       # analyse statique, comme en CI
```

Les tests nécessitant Postgres/Redis réels s'auto-skip si `TEST_DATABASE_URL` /
`TEST_REDIS_URL` ne sont pas définis (413 tests avec une base). ⚠️ Les 98 tests
ignorés comprennent **tous les tests de contrôle d'accès** — c'est pourquoi
l'intégration continue démarre un vrai service PostgreSQL. Voir
`agent-tuteur-api/README.md` pour le détail.

## Intégration continue

`.github/workflows/ci.yml` vérifie cinq choses sur chaque proposition de
modification : analyse statique (ruff), suite complète **contre un vrai
PostgreSQL**, fraîcheur du schéma OpenAPI, build du frontend Vue, et build de
l'image Docker de l'API **en Python 3.11** (les autres travaux tournent en 3.12 —
un épinglage valable seulement en 3.12 casserait le déploiement sans que rien ne
le signale).

## Limitation connue

Avec `VECTOR_BACKEND=memory` (défaut hors-ligne) **et** un worker ARQ dans un
processus séparé de l'API, chaque processus a son propre store en mémoire : un
document ingéré par le worker n'est pas visible en recherche côté API. Utiliser
`VECTOR_BACKEND=qdrant` (configuration par défaut de `docker-compose.dev.yml`)
dès qu'un worker séparé est utilisé — validé en conditions réelles (voir
[ADR 0002](docs/adr/0002-qdrant-plus-postgres.md) et
[ADR 0004](docs/adr/0004-ingestion-asynchrone-arq.md)).
