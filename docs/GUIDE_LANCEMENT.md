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

⚠️ **Deux frontends coexistent** dans le dépôt : le Next.js (courant) et le Vue
(historique, qui fait encore tourner le déploiement). Les commandes ci-dessus
lancent le **Vue** ; pour le Next.js, voir [§4.3](#43--quel-frontend--deux-coexistent).

Pour une **démo publique hébergée** (mono-conteneur SPA + API, sans worker ni
Qdrant), voir [`DEPLOIEMENT_RENDER.md`](DEPLOIEMENT_RENDER.md).

---

## 2. Prérequis

- Python 3.11+ (les travaux de CI tournent en 3.12, **l'image Docker en 3.11** —
  un épinglage valable seulement en 3.12 casse le déploiement, cf. §10)
- Node.js 20+ et npm (pour les frontends, modes B/C ; inutile en mode A où le
  frontend est construit dans une image Docker)
- Docker + Docker Compose (modes A et B)
- `make` (GNU Make)

### Installation des dépendances (une fois, tous modes confondus)

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r agent-tuteur-api/requirements.txt
.venv/bin/pip install -e 'agent-tuteur-api[parsing,dev]'
cd agent-tuteur-web && npm install && cd ..
```

Ou, pour la partie couverte : `make setup` (⚠️ `make setup` n'installe **pas**
l'extra `parsing` — voir l'avertissement ci-dessous).

⚠️ **Ne pas sauter l'extra `parsing`** (PyMuPDF). Sans lui, la lecture des PDF
retombe silencieusement sur `pypdf`, qui aplatit ou perd fractions, indices et
exposants et se trompe souvent sur l'ordre de lecture des colonnes. Le corpus
étant à 100 % des mathématiques du secondaire, l'ingestion « réussit » en
abîmant le contenu — seule une ligne de journal le signale.

⚠️ **Si un environnement conda est actif** (`conda activate ...`) au moment de
créer le venv, `pyvenv.cfg` peut enregistrer le mauvais interpréteur de base et
provoquer des `Segmentation fault`/`ImportError` sur des modules natifs
(`ctypes`, `sympy`...) plus tard. Fais `conda deactivate` avant `python3 -m venv`,
ou force un interpréteur explicite : `/usr/bin/python3.12 -m venv .venv`. Voir
[§10](#10-dépannage) si le symptôme apparaît malgré tout.

---

## 3. Mode A — Tout Docker (docker-compose)

Le plus simple : une seule commande démarre Postgres, Redis, Qdrant, applique
les migrations, puis lance l'API, le worker et le frontend web (Vue).

```bash
cd agent-tuteur-deploy
docker compose -f docker-compose.dev.yml up -d --build
```

- Frontend web : http://localhost:8080
- API : http://localhost:8000/docs
- Health : http://localhost:8000/health

**Créer le premier compte admin** (obligatoire — l'API exige désormais une
authentification, et aucun compte n'existe par défaut) :

```bash
docker compose -f docker-compose.dev.yml --profile seed run --rm createadmin
# défaut : admin@tuteur.sn / changeme123 — surcharge : ADMIN_EMAIL=… ADMIN_PASSWORD=…
```

Se connecter ensuite sur http://localhost:8080 avec ces identifiants. Créer des
comptes élèves/admin supplémentaires depuis l'espace **Administration → Comptes**.

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

⚠️ Si les ports 5432/6379/6333/8000/8080 sont déjà occupés par d'autres
services sur ta machine, remappe-les dans un fichier d'override (`-f
docker-compose.dev.yml -f override.yml`) plutôt que d'éditer le fichier commité.

---

## 4. Mode B — Infra Docker + code local (recommandé en dev actif)

Postgres/Redis/Qdrant tournent en conteneurs jetables ; l'API/worker tournent en
local avec **rechargement à chaud** (`uvicorn --reload`), et le frontend web via
le serveur de dev Vite (`npm run dev`, proxy `/api` → :8000, HMR) — le mode le
plus confortable pour itérer sur le code.

Après `make migrate`, créer un compte admin local (sans lui, impossible de se
connecter) :

```bash
make createadmin EMAIL=admin@tuteur.sn PASSWORD=changeme123
```

Le frontend Vite est servi sur http://localhost:5173 (mode B/C), l'API sur
http://localhost:8000.

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

### 4.3 — Quel frontend ? (deux coexistent)

| Répertoire | Techno | Statut | Lancé par |
|---|---|---|---|
| `agent-tuteur-web-next/` | Next.js 16 / React 19 / TypeScript | **Frontend courant**, 9 écrans | `npm run dev` (voir ci-dessous) |
| `agent-tuteur-web/` | Vue 3 (Vite) | Historique — fait encore tourner le déploiement | `make run`, `make dev`, `docker-compose.dev.yml` |

Le Vue reste ce que lancent `make dev` / le compose **tant que la bascule du
déploiement n'est pas décidée** (point V7, cf. `docs/STATUS.md` §5). Les deux
sont construits par l'intégration continue.

**Lancer le frontend Next.js** :

```bash
cd agent-tuteur-web-next
npm install
npm run gen:api                                   # types TypeScript depuis openapi.json
API_ORIGIN=http://localhost:8000 npm run dev      # http://localhost:3000
```

Ce que vérifie la CI, à lancer avant de proposer une modification :

```bash
npm run gen:api && git diff --exit-code src/types/api.d.ts   # types à jour ?
npm run typecheck
npm run build
```

⚠️ **`API_ORIGIN` est lu au *build*, pas au démarrage.** Next fige les
redirections dans le manifeste de construction : un `npm run build` sans cette
variable produit une image qui pointera **toujours** vers `localhost:8000`, quoi
qu'on mette dans l'environnement ensuite. Piège vérifié en conditions réelles.

Le navigateur ne connaît jamais l'URL du backend : l'API est jointe par chemin
relatif `/api/...`, redirigé par Next en dev et par nginx en production. C'est ce
qui évite d'ouvrir CORS.

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

### 6.2 — `LLM_CHAIN` et `LLM_BACKEND`

Deux réglages, et **`LLM_CHAIN` l'emporte** quand il est renseigné.

#### `LLM_CHAIN` — ordre explicite (recommandé)

```bash
LLM_CHAIN=gemini,mistral,mock
```

Impose la chaîne, sans toucher au code. Changer de fournisseur principal devient
un réglage de `.env` réversible plutôt qu'une modification à redéployer. Les
valeurs acceptées sont `mistral`, `gemini`, `ollama`, `mock`.

#### `LLM_BACKEND` — composition automatique (`LLM_CHAIN` vide)

| Valeur | Chaîne de fallback résultante |
|---|---|
| `auto` (défaut) | clé Mistral → `Mistral → Gemini → Ollama → Mock` ; sinon clé Gemini → `Gemini → Ollama → Mock` ; sinon Ollama joignable → `Ollama → Mock` ; sinon `Mock` |
| `mistral` | Mistral → Mock (jamais bloquant même en forçant Mistral) |
| `gemini` | Gemini → Mock |
| `ollama` | Ollama → Mock |
| `mock` | Mock seul (déterministe, aucun réseau — utile en test/CI) |

Clés et modèles associés : `MISTRAL_API_KEY` / `MISTRAL_MODEL`
(`mistral-small-latest`), `GEMINI_API_KEY` / `GEMINI_MODEL`
(`gemini-2.5-flash`), `OLLAMA_BASE_URL` / `OLLAMA_MODEL` (`qwen3:8b`).

Le mock est **toujours** le dernier maillon : la génération ne bloque jamais, et
un élève ne reçoit jamais un mode d'emploi de configuration à la place d'une
réponse. Voir `GET /health` → champ `llm` pour la chaîne effective.

> **En streaming** : si un fournisseur échoue *avant* d'avoir émis le moindre
> token, on passe au suivant ; s'il échoue *après* avoir déjà streamé, l'erreur
> est propagée — un flux partiel ne peut pas être rejoué proprement.

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

Test rapide du chat (l'API exige un jeton JWT — se connecter d'abord) :

```bash
# 1) Login → récupère un jeton (compte créé via `make createadmin` ou le profil seed)
TOKEN=$(curl -s http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@tuteur.sn", "password": "changeme123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2) Chat streamé (le student_id est dérivé du jeton, plus besoin de le passer)
curl -sN -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "comment dériver un quotient de fonctions ?"}'
```

Sans jeton, toute route métier renvoie `401`. `/health` reste public.

### Routes pédagogiques (issues de la fusion)

```bash
# Générer un quiz (quiz_type : "qcm" ou "vrai_faux")
curl -s -X POST http://localhost:8000/api/quiz \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"competence": "Dérivation", "quiz_type": "qcm",
       "curriculum_context": {"classe": "Terminale", "serie": "S1"}}'

# Répondre : le quiz_token reçu ci-dessus + l'identifiant du choix
curl -s -X POST http://localhost:8000/api/quiz/answer \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"quiz_token": "eyJ...", "answer": "A"}'

# Maîtrise et évaluation d'un élève
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/mastery/$STUDENT_ID
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/evaluation/$STUDENT_ID
```

Trois comportements à connaître :

- **La bonne réponse ne descend jamais dans le navigateur.** Elle voyage scellée
  dans `quiz_token`, signé côté serveur (validité 60 min) : le client le
  transporte sans pouvoir le lire ni le modifier. La correction se fait
  serveur-side, par comparaison déterministe de deux identifiants.
- `available: false` (avec `choices: []`) n'est **pas une erreur HTTP** : c'est
  le résultat honnête d'un modèle qui n'a rien produit d'exploitable après deux
  tentatives. L'interface propose de réessayer — **jamais de QCM factice** aux
  propositions « Option 1 / Option 2 », qui donnerait l'illusion d'un exercice.
- Sans `competence` **ni** indication exploitable dans `curriculum_context`
  (`chapitre`, puis `competence`, puis `discipline`) → **422** : on n'interroge
  jamais un élève au hasard.

Le contrôle d'accès est centralisé : un parent ou un enseignant ne peut lire la
maîtrise que des élèves auxquels son compte est **explicitement lié** (table
`student_links`). Un `403` ici est le comportement attendu, pas un bug de
configuration. Schémas exacts de chaque route : [`api.md`](api.md).

---

## 8. Logs et observabilité

Chaque événement (nœud d'agent, étape d'ingestion) est loggé en JSON, sur
stdout et dans un fichier dédié par service :

```bash
tail -f agent-tuteur-api/logs/api.log agent-tuteur-api/logs/worker.log
```

Vue consolidée et lisible dans le frontend web → espace **Administration → 🪵 Logs**
(orchestration agent tour par tour ; les étapes d'ingestion par document sont
visibles dans **Administration → Documents**).
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
pkill -f "vite"           # serveur de dev du frontend Vue
pkill -f "next dev"       # serveur de dev du frontend Next.js
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

### Les tests échouent en cascade (~26 échecs) sans raison apparente

`pytest` a été lancé **depuis la racine du dépôt**. La configuration et
l'environnement ne sont pas trouvés depuis ce répertoire de travail. Toujours
lancer depuis `agent-tuteur-api/` :

```bash
cd agent-tuteur-api && ../.venv/bin/python -m pytest -q     # 317 passed, 98 skipped
```

Les 98 tests ignorés comprennent **tous les tests de contrôle d'accès** : ils
exigent un vrai PostgreSQL (`TEST_DATABASE_URL`). Ne jamais conclure « tout
passe » sans eux — c'est pourquoi la CI démarre un service Postgres.

### L'image Docker de l'API ne se construit pas alors que la CI est verte

Les travaux de CI tournent en **Python 3.12**, mais l'image Docker est en
**3.11** (le plancher déclaré par `pyproject.toml`). Un épinglage valable
seulement en 3.12 casse donc le déploiement sans qu'aucun test ne le signale —
c'est exactement ce qui s'est produit avec `numpy==2.5.1`, qui exige 3.12. D'où
le travail `image-api` dans `.github/workflows/ci.yml`, qui construit l'image à
chaque proposition de modification. Vérifier tout nouvel épinglage sous 3.11.

### `PyMuPDF` absent — formules mathématiques dégradées

Symptôme discret : l'ingestion **réussit**, mais les fractions, indices et
exposants des PDF sont aplatis ou perdus, et le RAG répond à côté. Seule une
ligne de journal signale le repli sur `pypdf`. Correctif :

```bash
.venv/bin/pip install -e 'agent-tuteur-api[parsing]'
```

Puis ré-indexer les documents concernés (`POST /api/documents/{id}/reindex`).

### Ports déjà occupés (5432, 6379, 6333, 8000, 8080, 5173, 3000)

Fréquent si un Postgres/Redis natif tourne déjà sur la machine pour un autre
projet. Utiliser des ports hôte différents dans les commandes `docker run`
(ex. `-p 55432:5432`) et adapter `DATABASE_URL`/`REDIS_URL`/`QDRANT_URL` en
conséquence — les ports **internes** au conteneur restent inchangés.

### `401 Unauthorized` sur toutes les routes / impossible de se connecter

L'API exige un jeton JWT (`Authorization: Bearer …`). Si aucun compte n'existe
encore, en créer un : `make createadmin EMAIL=… PASSWORD=…` (local) ou le profil
`seed` du compose (Docker). `/health` reste la seule route publique. Un `401`
après un login réussi signale un jeton expiré (durée `JWT_EXPIRY_HOURS`, 7 j par
défaut) — se reconnecter. Vérifier aussi que `JWT_SECRET` est identique entre les
redémarrages de l'API (un secret changé invalide les jetons émis).

### RLS ne filtre rien en production

Le rôle de connexion (`DATABASE_URL`) doit être **non-superuser**
(`postgres-init/01-app-role.sh` dans `agent-tuteur-deploy/`). Un superuser
Postgres contourne toujours Row Level Security, même avec
`FORCE ROW LEVEL SECURITY`. Sans objet en dev local (le rôle `tuteur` par
défaut est superuser, RLS inopérante mais sans conséquence hors multi-tenant
réel) — voir `docs/adr/0006-tenant-id-des-le-depart.md`.
