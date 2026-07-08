# Guide de lancement — Agent Tuteur Sénégal

Référence pratique pour lancer le projet, en local ou via Docker, avec toutes
les combinaisons de configuration possibles. Complète `docs/architecture.md`
(pourquoi) avec le « comment » opérationnel.

---

## Table des matières

1. [Vue d'ensemble des modes](#1-vue-densemble-des-modes)
2. [Prérequis](#2-prérequis)
3. [Mode A — Tout Docker (docker-compose)](#3-mode-a--tout-docker-docker-compose)
4. [Mode B — Infra Docker + code local (recommandé en dev actif)](#4-mode-b--infra-docker--code-local-recommandé-en-dev-actif)
5. [Mode C — Tout local sans Docker](#5-mode-c--tout-local-sans-docker)
6. [Configurations possibles (.env)](#6-configurations-possibles-env)
7. [Vérification](#7-vérification)
8. [Logs et observabilité](#8-logs-et-observabilité)
9. [Arrêt propre](#9-arrêt-propre)
10. [Dépannage](#10-dépannage)

---

## 1. Vue d'ensemble des modes

| Mode | Commande principale | Infra à lancer soi-même | Cas d'usage |
|---|---|---|---|
| **A — Tout Docker** | `docker compose -f docker-compose.dev.yml up` | Rien (tout est dans le compose) | Démo complète, onboarding rapide, réplique la prod |
| **B1 — Hybride minimal** | `make -j2 api run` | Postgres seul | Dev actif quotidien, itération rapide sur le code |
| **B2 — Hybride complet** | `make dev` | Postgres + Redis + Qdrant | Tester le worker ARQ et le vectorstore Qdrant réellement |
| **C — Tout local** | `make dev` (Postgres/Redis natifs, pas Docker) | Postgres + Redis installés sur la machine | Environnement sans Docker disponible |

Le code applicatif (API, worker, frontend) est **identique** dans les 3 modes —
seule la façon de lancer l'infrastructure et les processus change.

---

## 2. Prérequis

- Python 3.11+ (le projet a été validé avec 3.12)
- Docker + Docker Compose (modes A et B)
- `make` (GNU Make)

### Installation des dépendances (une fois, tous modes confondus)

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r agent-tuteur-api/requirements.txt -e agent-tuteur-api
.venv/bin/pip install -r agent-tuteur-frontend/requirements.txt
```

Ou, équivalent : `make setup`.

⚠️ **Si un environnement conda est actif** (`conda activate ...`) au moment de
créer le venv, `pyvenv.cfg` peut enregistrer le mauvais interpréteur de base et
provoquer des `Segmentation fault`/`ImportError` sur des modules natifs
(`ctypes`, `sympy`...) plus tard. Fais `conda deactivate` avant `python3 -m venv`,
ou force un interpréteur explicite : `/usr/bin/python3.12 -m venv .venv`. Voir
[§10](#10-dépannage) si le symptôme apparaît malgré tout.

---

## 3. Mode A — Tout Docker (docker-compose)

Le plus simple : une seule commande démarre Postgres, Redis, Qdrant, applique
les migrations, puis lance l'API, le worker et le frontend.

```bash
cd agent-tuteur-deploy
docker compose -f docker-compose.dev.yml up -d --build
```

- API : http://localhost:8000/docs
- Frontend : http://localhost:8501
- Health : http://localhost:8000/health

**Arrêt** :

```bash
docker compose -f docker-compose.dev.yml down        # garde les volumes (données conservées)
docker compose -f docker-compose.dev.yml down -v      # supprime aussi les volumes
```

**Rebuild après modification du code** :

```bash
docker compose -f docker-compose.dev.yml up -d --build api worker
```

**Production** : `docker-compose.prod.yml` (secrets via `.env.prod`, nginx en
frontal). Voir `agent-tuteur-deploy/scripts/setup.sh` et `deploy.sh`.

⚠️ Si les ports 5432/6379/6333/8000/8501 sont déjà occupés par d'autres
services sur ta machine, remappe-les dans un fichier d'override (`-f
docker-compose.dev.yml -f override.yml`) plutôt que d'éditer le fichier commité.

---

## 4. Mode B — Infra Docker + code local (recommandé en dev actif)

Postgres/Redis/Qdrant tournent en conteneurs jetables ; l'API/worker/frontend
tournent en local avec **rechargement à chaud** (`uvicorn --reload`) — le mode
le plus confortable pour itérer sur le code.

### 4.1 — B1 : minimal (Postgres seul, sans worker)

Le plus léger : pas de Redis, pas de Qdrant, pas de worker séparé. L'ingestion
passe par `BackgroundTasks` dans le même processus que l'API (dégradation
gracieuse déjà prévue).

```bash
docker run -d --name tutor-pg -e POSTGRES_USER=tuteur -e POSTGRES_PASSWORD=tuteur -e POSTGRES_DB=tuteur -p 55432:5432 postgres:16-alpine
```

`.env` :

```bash
cat > agent-tuteur-api/.env <<'EOF'
DATABASE_URL=postgresql+asyncpg://tuteur:tuteur@localhost:55432/tuteur
VECTOR_BACKEND=memory
EMBEDDING_BACKEND=light
LLM_BACKEND=auto
MISTRAL_API_KEY=
EOF
make migrate
make -j2 api run
```

**Important** : dans ce mode, ne lance **pas** `make worker` en plus — avec
`VECTOR_BACKEND=memory`, un worker en processus séparé aurait son propre
vectorstore, distinct de celui de l'API (limitation documentée, voir §6).

### 4.2 — B2 : complet (Postgres + Redis + Qdrant + worker)

Reproduit fidèlement la configuration de production (worker séparé, store
vectoriel partagé).

```bash
docker run -d --name tutor-pg -e POSTGRES_USER=tuteur -e POSTGRES_PASSWORD=tuteur -e POSTGRES_DB=tuteur -p 55432:5432 postgres:16-alpine
docker run -d --name tutor-redis -p 56379:6379 redis:7-alpine
docker run -d --name tutor-qdrant -p 6333:6333 qdrant/qdrant:latest
```

`.env` :

```bash
cat > agent-tuteur-api/.env <<'EOF'
DATABASE_URL=postgresql+asyncpg://tuteur:tuteur@localhost:55432/tuteur
REDIS_URL=redis://localhost:56379/0
VECTOR_BACKEND=qdrant
QDRANT_URL=http://localhost:6333
EMBEDDING_BACKEND=light
LLM_BACKEND=auto
MISTRAL_API_KEY=
EOF
make migrate
make dev        # = make -j3 api worker run
```

Ou séparément (3 terminaux, pratique pour voir les logs de chacun) :

```bash
make api        # terminal 1
make worker     # terminal 2
make run        # terminal 3
```

---

## 5. Mode C — Tout local sans Docker

Si Docker n'est pas disponible : installe Postgres et Redis nativement (via le
gestionnaire de paquets du système), crée un rôle/une base, puis suis
exactement les mêmes étapes que le mode B en adaptant `DATABASE_URL`/`REDIS_URL`
vers `localhost` (ports standards 5432/6379, ou ceux choisis à l'installation).

```bash
# Exemple Debian/Ubuntu (à adapter selon la distribution)
sudo apt install postgresql redis-server
sudo -u postgres createuser tuteur -P
sudo -u postgres createdb tuteur -O tuteur
```

Le reste est identique au mode B (`.env`, `make migrate`, `make dev`).
`VECTOR_BACKEND=memory` reste disponible si Qdrant n'est pas installé (mêmes
règles qu'en §4.1).

---

## 6. Configurations possibles (.env)

### 6.1 — `VECTOR_BACKEND`

| Valeur | Comportement | Repli si indisponible |
|---|---|---|
| `memory` (défaut) | Store en mémoire du processus, aucun serveur requis | — |
| `qdrant` | Store persistant partagé entre processus | **Aucun** — l'API plante au démarrage si Qdrant est injoignable (`ResponseHandlingException`) |

⚠️ **Piège à connaître** : avec `memory`, **chaque processus a son propre
store**. Si l'API et le worker tournent séparément (mode B2/C avec worker),
un document ingéré par le worker n'apparaît pas en recherche côté API. Deux
solutions : soit ne pas lancer de worker séparé (mode B1, ingestion dans le
même processus que l'API), soit passer en `VECTOR_BACKEND=qdrant`.

### 6.2 — `LLM_BACKEND`

| Valeur | Chaîne de fallback résultante |
|---|---|
| `auto` (défaut) | Mistral (si clé fournie) → Ollama (si joignable) → Mock |
| `mistral` | Mistral → Mock (jamais bloquant même en forçant Mistral) |
| `ollama` | Ollama → Mock |
| `mock` | Mock seul (déterministe, aucun réseau — utile en test/CI) |

Le mock ne donne jamais d'erreur : c'est le dernier maillon de la chaîne dans
tous les cas. Voir `GET /health` → champ `llm` pour la chaîne effective.

### 6.3 — Faut-il lancer `make worker` ?

| Situation | `make worker` nécessaire ? |
|---|---|
| Je veux juste tester le chat/l'agent | Non |
| Je veux tester l'upload de documents | Non — `BackgroundTasks` suffit (même processus que l'API) |
| Je veux valider la vraie mécanique de queue ARQ | Oui — nécessite Redis actif |
| `VECTOR_BACKEND=qdrant` et je veux la cohérence complète upload→recherche en multi-process | Oui |

`make worker` **exige** Redis pour démarrer (pas de repli — contrairement à
l'API, dont le pool ARQ est optionnel). Sans Redis, `make worker` échoue avec
`ConnectionError` après 5 tentatives ; c'est attendu, pas un bug.

### 6.4 — Tableau récapitulatif des combinaisons

| `VECTOR_BACKEND` | Worker séparé lancé ? | Redis requis ? | Qdrant requis ? | Résultat |
|---|---|---|---|---|
| `memory` | Non | Non | Non | ✅ Fonctionne, le plus simple |
| `memory` | Oui | Oui (pour le worker) | Non | ⚠️ Fonctionne mais incohérent (stores séparés) |
| `qdrant` | Non | Non | **Oui** | ✅ Fonctionne (upload via BackgroundTasks) |
| `qdrant` | Oui | Oui | **Oui** | ✅ Configuration complète, recommandée en pré-prod |

---

## 7. Vérification

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

```json
{
  "status": "ok",
  "db": true,
  "redis": "ok",
  "qdrant": "ok",
  "llm": ["mistral", "ollama", "mock"]
}
```

- `db` : `false` → Postgres injoignable, rien ne fonctionnera (mandataire dans
  tous les modes).
- `redis` : `"degraded"` → pas de pool ARQ, ingestion en `BackgroundTasks`
  (normal en mode B1).
- `qdrant` : `"not_configured"` si `VECTOR_BACKEND=memory` ; `"ok"`/`"unreachable"` sinon.

Test rapide du chat :

```bash
curl -sN -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "comment dériver un quotient de fonctions ?", "student_id": "test"}'
```

---

## 8. Logs et observabilité

Chaque événement (nœud d'agent, étape d'ingestion) est loggé en JSON, sur
stdout et dans un fichier dédié par service :

```bash
tail -f agent-tuteur-api/logs/api.log agent-tuteur-api/logs/worker.log
```

Vue consolidée et lisible dans le frontend Streamlit → page **🪵 Logs**
(orchestration agent tour par tour, et étapes d'ingestion par document).
Détail complet : `docs/RAPPORT_TECHNIQUE.md` §8 et `agent_tuteur/observability.py`.

---

## 9. Arrêt propre

**Mode A (docker-compose)** :

```bash
docker compose -f docker-compose.dev.yml down
```

**Modes B/C (processus locaux)** :

```bash
pkill -f "uvicorn agent_tuteur"
pkill -f "arq agent_tuteur"
pkill -f "streamlit run"
```

(`make dev` avec `Ctrl+C` arrête les 3 en une fois s'ils ont été lancés via
cette cible.)

**Conteneurs jetables (modes B/C)** :

```bash
docker stop tutor-pg tutor-redis tutor-qdrant
docker rm tutor-pg tutor-redis tutor-qdrant
```

---

## 10. Dépannage

### `ResponseHandlingException` / `Connection refused` au démarrage de l'API

`VECTOR_BACKEND=qdrant` mais aucun Qdrant ne répond sur `QDRANT_URL`. Soit
lancer Qdrant (`docker run -d -p 6333:6333 qdrant/qdrant:latest`), soit passer
`VECTOR_BACKEND=memory` dans `.env`.

### `redis.exceptions.ConnectionError` sur `make worker`

Attendu si Redis n'est pas lancé — le worker en a besoin pour démarrer
(contrairement à l'API). Soit démarrer Redis, soit ne pas lancer `make worker`
(mode B1, §4.1).

### `Segmentation fault (core dumped)` sur `make api`/`make worker`/`make run`

Symptôme d'un `.venv` corrompu (le plus souvent : créé pendant qu'un
environnement conda était actif, causant une incohérence entre `pyvenv.cfg` et
les liens symboliques réels de `.venv/bin/`). Vérifier :

```bash
cat .venv/pyvenv.cfg   # le champ "home" doit correspondre à l'interpréteur réellement utilisé
.venv/bin/python -c "import ctypes"   # doit s'exécuter sans erreur
```

Si l'import échoue ou que `home` pointe vers un environnement inattendu (ex.
`miniforge3/envs/...`), reconstruire le venv depuis un interpréteur système
explicite :

```bash
rm -rf .venv
/usr/bin/python3.12 -m venv --without-pip .venv
.venv/bin/python <(curl -sL https://bootstrap.pypa.io/get-pip.py)
make setup
```

### Ports déjà occupés (5432, 6379, 6333, 8000, 8501)

Fréquent si un Postgres/Redis natif tourne déjà sur la machine pour un autre
projet. Utiliser des ports hôte différents dans les commandes `docker run`
(ex. `-p 55432:5432`) et adapter `DATABASE_URL`/`REDIS_URL`/`QDRANT_URL` en
conséquence — les ports **internes** au conteneur restent inchangés.

### RLS ne filtre rien en production

Le rôle de connexion (`DATABASE_URL`) doit être **non-superuser**
(`postgres-init/01-app-role.sh` dans `agent-tuteur-deploy/`). Un superuser
Postgres contourne toujours Row Level Security, même avec
`FORCE ROW LEVEL SECURITY`. Sans objet en dev local (le rôle `tuteur` par
défaut est superuser, RLS inopérante mais sans conséquence hors multi-tenant
réel) — voir `docs/adr/0006-tenant-id-des-le-depart.md`.
