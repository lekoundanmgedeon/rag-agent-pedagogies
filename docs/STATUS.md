# État de reprise — Agent Tuteur Sénégal

*Dernière mise à jour : 2026-08-07, après la fusion NURU × ATS. Point de reprise
pour une nouvelle session (humaine ou Claude) — pas une doc de référence finale
(voir l'index ci-dessous).*

> **Où en est le projet** : la fusion des dépôts NURU et ATS est **terminée et
> fusionnée dans `main`** (commit de merge `064db7e`, 2026-08-06). Les huit
> modules du plan (M0 à M8) sont traités. Il reste **sept points en attente
> d'arbitrage d'équipe** (V1 à V7, §5) dont un seul bloque une mise en
> production : la bascule du déploiement vers le frontend Next.js.

---

## 1. Où trouver quoi (ne pas dupliquer ici)

| Besoin | Document |
|---|---|
| Vue d'ensemble, démarrage rapide | [`README.md`](../README.md) (racine) |
| Architecture, flux, frontières, domaine pédagogique | [`docs/architecture.md`](architecture.md) |
| Chaque endpoint de l'API | [`docs/api.md`](api.md) |
| Décisions techniques argumentées | [`docs/RAPPORT_TECHNIQUE.md`](RAPPORT_TECHNIQUE.md) |
| **Comment lancer (Docker/local, tous modes)** | [`docs/GUIDE_LANCEMENT.md`](GUIDE_LANCEMENT.md) |
| **Mettre en ligne sur un VPS (test d'équipe)** | [`docs/DEPLOIEMENT_TEST.md`](DEPLOIEMENT_TEST.md) |
| ADR individuelles (dont **0010** sur la fusion) | [`docs/adr/`](adr/) |
| Import de données antérieures | [`docs/migration.md`](migration.md) |
| **Résultat de la fusion, pour la réunion** | [`docs/RAPPORT_FUSION.md`](RAPPORT_FUSION.md) |
| **Journal de la fusion, module par module** | [`JOURNAL_FUSION.md`](../JOURNAL_FUSION.md) (racine) |
| Historique d'avancement de la fusion (archive) | [`REPRISE_FUSION.md`](../REPRISE_FUSION.md) (racine) |
| Comparatif d'origine avec `nuru-binta` (archive) | [`docs/COMPARATIF_ARCHITECTURES.md`](COMPARATIF_ARCHITECTURES.md) |
| Version courte du comparatif pour la réunion (archive) | [`docs/SYNTHESE_REUNION_TECHNIQUE.md`](SYNTHESE_REUNION_TECHNIQUE.md) |
| Schémas et extraits de refactoring de la cible (archive) | [`docs/ARCHITECTURE_CIBLE.md`](ARCHITECTURE_CIBLE.md) |

Les quatre derniers décrivent le projet **tel qu'il était prévu** avant
exécution. Ils portent un bandeau en tête et ne sont pas maintenus à jour :
pour l'état réel, s'en tenir aux documents de la première moitié du tableau.

---

## 2. Ce qui est fait

### 2.1 Socle initial (étapes 1 à 8)

Cœur RAG + agent LangGraph (indices 0-4, détection de frustration, garde-fous,
chaîne de repli LLM) + persistance PostgreSQL avec RLS + API FastAPI (SSE) +
ingestion asynchrone ARQ + frontend web + déploiement Docker Compose +
documentation. Détail : [`RAPPORT_TECHNIQUE.md`](RAPPORT_TECHNIQUE.md).

Ajouts ultérieurs au socle : authentification **JWT + rôles** (bascule dure,
plus d'en-tête `X-Tenant-Id`), logging JSON structuré avec trace d'orchestration
nœud par nœud, et détection des documents **orphelins** (`indexed` en base mais
vecteurs absents du store — `POST /api/documents/verify-all` + vérification au
démarrage).

> Le frontend Streamlit historique (`agent-tuteur-frontend/`) a été **supprimé
> du dépôt le 2026-07-30** ; il reste récupérable dans l'historique git. Toute
> mention de Streamlit ailleurs dans la documentation est historique.

### 2.2 Fusion NURU × ATS (modules M1 à M8)

| Module | Apport | Où c'est écrit |
|---|---|---|
| **M1** | Lecture PDF par **PyMuPDF** (`pypdf` détruisait les formules) + 3 extracteurs de métadonnées portés de NURU | `ingestion/loaders/` |
| **M2** | Re-ranker **cours/complément** au-dessus du RRF : le cours remonte quand l'élève demande une explication, et l'agent avoue quand le corpus n'a que des TD | `vectorstore/retriever.py` |
| **M3** | Modèle de données pédagogique (5 tables) + rôles étendus | migrations `0006`, `0007` |
| **M4** | Troisième posture **quiz** : interroger, vérifier de façon déterministe, enregistrer la maîtrise | `agent/quiz.py`, `agent/verify.py`, `domain/mastery.py` |
| **M5** | Routes `/api/quiz`, `/api/quiz/answer`, `/api/evaluation/{id}`, `/api/mastery/{id}`, toutes protégées par une règle d'accès centralisée | `api/routes/`, `api/dependencies.py` |
| **M6** | **Gemini** ajouté comme fournisseur ; l'ordre de la chaîne de repli devient le réglage `.env` `LLM_CHAIN` | `agent/llm/router.py` |
| **M7** | ADR 0010, dépendances épinglées, ruff configuré, **intégration continue** (5 travaux) | `.github/workflows/ci.yml` |
| **M8** | Frontend **Next.js 16 / React 19 / TypeScript**, 9 écrans, contrat d'API généré depuis OpenAPI | `agent-tuteur-web-next/` |

Le détail de chaque décision — ce qui a été gardé, écarté et pourquoi — est dans
[`JOURNAL_FUSION.md`](../JOURNAL_FUSION.md), une section par module.

### 2.3 Garde-fou anti-divergence (à connaître avant de modifier une route)

Le contrat d'API est **versionné et vérifié en CI**. Après toute modification
d'une route ou d'un schéma :

```bash
cd agent-tuteur-api    && python scripts/export_openapi.py openapi.json
cd agent-tuteur-web-next && npm run gen:api
```

Sans ces deux commandes, la CI échoue (elle régénère et exige zéro différence).
C'est ce qui garantit que renommer un champ côté API **casse la compilation** du
frontend au lieu de passer inaperçu.

---

## 3. État vérifié au 2026-08-07

| Vérification | Résultat | Commande |
|---|---|---|
| Tests sans base de données | **317 passés, 98 ignorés** ✅ | `cd agent-tuteur-api && ../.venv/bin/python -m pytest -q` |
| Analyse statique | **All checks passed!** ✅ | `cd agent-tuteur-api && ../.venv/bin/ruff check .` |
| Tests avec PostgreSQL | **413** — chiffre du 2026-08-04, *non revérifié* (la base jetable `fusion-pg-test` n'existe plus) | voir §4.2 |

Les 98 tests ignorés sans base ne sont pas anodins : ils comprennent **tous les
tests de contrôle d'accès**. C'est précisément pour cela que la CI fait tourner
un service PostgreSQL — ne jamais conclure « tout passe » sur la seule foi des
317.

### Travail non commité

```
M agent-tuteur-web-next/next-env.d.ts
```

Un seul fichier, **généré automatiquement par Next.js** (le chemin des types de
routes est passé de `./.next/types/` à `./.next/dev/types/` au premier
`npm run dev`). Sans conséquence : ce fichier porte la mention « should not be
edited ». À committer ou à ignorer selon la préférence.

### Conteneurs Docker actifs

La stack complète `docker-compose.dev.yml` tourne (préfixe
`agent-tuteur-senegal-*`) : postgres, redis, qdrant, api (`:8000`),
worker, et le frontend **Vue** (`:8080`) — pas le Next.js, la bascule n'étant
pas faite (point V7).

> ⚠️ Les conteneurs `nuru_postgres`, `nuru_redis` et `erp-db-demo` qui tournent
> sur cette machine **ne nous appartiennent pas** — ne jamais les arrêter.

---

## 4. Reprendre rapidement

### 4.1 Vérifier que l'état est sain

```bash
cd /home/aimssn/nuru/rag-agent-pedagogie
git log --oneline -5
docker ps --format "{{.Names}}: {{.Ports}}"     # la stack tourne-t-elle encore ?

cd agent-tuteur-api
../.venv/bin/python -m pytest -q                # doit afficher 317 passed
../.venv/bin/ruff check .                       # doit afficher : All checks passed!
```

Si la stack est arrêtée : `cd agent-tuteur-deploy && docker compose -f docker-compose.dev.yml up -d`.

### 4.2 Recréer la base de test jetable (pour les 413 tests)

```bash
docker run -d --name fusion-pg-test \
  -e POSTGRES_PASSWORD=test -e POSTGRES_USER=test -e POSTGRES_DB=fusion \
  -p 55432:5432 postgres:16-alpine

cd agent-tuteur-api
DATABASE_URL="postgresql+asyncpg://test:test@localhost:55432/fusion" \
  ../.venv/bin/alembic upgrade head

TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost:55432/fusion" \
  ../.venv/bin/python -m pytest -q
```

Le port 55432 a été choisi pour ne percuter aucun service existant sur la machine.

### 4.3 Lancer le frontend Next.js

```bash
cd agent-tuteur-web-next
npm install
npm run gen:api                                   # types depuis le schéma OpenAPI
API_ORIGIN=http://localhost:8000 npm run dev
npm run typecheck && npm run build                # ce que vérifie la CI
```

⚠️ **`API_ORIGIN` est lu au *build*, pas au démarrage** — vérifié. La changer
sans reconstruire n'a aucun effet.

### 4.4 Dépendance à ne pas oublier sur une machine neuve

```bash
pip install -r requirements.txt      # versions exactes validées
pip install -e '.[parsing,dev]'      # PyMuPDF + ruff
```

Sans l'extra `parsing`, la lecture des PDF retombe silencieusement sur `pypdf`
et **abîme les formules** — seule une ligne de journal le signale.

### 4.5 Le corpus

Les 103 PDF sont dans `~/nuru/nuru-binta/data/raw/` (dossiers `cours/` et
`exercices/`). Ils ne sont **pas** dans ce dépôt, conformément au plan.

---

## 5. Ce qui reste — sept points en attente d'arbitrage

Le code n'a été modifié dans aucun sens sur ces points : ils demandent une
décision d'équipe. Détail et options dans la section « ⚠️ Points à valider » de
[`JOURNAL_FUSION.md`](../JOURNAL_FUSION.md).

| # | Sujet | Gravité |
|---|---|---|
| **V1** | **57 % du corpus serait invisible** à une recherche filtrée par série (mesuré : 59 documents sur 103) | 🔴 **le plus important** |
| V2 | Faut-il porter `NougatAdapter` ? (non porté : l'implémentation de NURU ne fonctionne pas) | 🟢 faible |
| V3 | Que faire de la ligne « Compétences » des documents ? | 🟢 faible |
| V4 | Le jeu d'évaluation de recherche n'existe pas → les gains du M2 ne sont pas mesurés | 🟠 moyenne |
| V5 | Une bonne explication de quiz peut être jetée par une règle trop stricte | 🟢 faible |
| V6 | Faut-il persister les quiz en base (pour analyser la qualité des questions) ? | 🟢 faible |
| **V7** | **Basculer le déploiement vers le frontend Next.js** (touche la production) | 🟠 moyenne |

**V1 est à traiter en priorité** : il touche la décision D5 du comparatif
(filtrage curriculaire) et conditionne l'utilité réelle du corpus. Il révèle
aussi qu'une partie du dossier `cours/` est constituée de polycopiés **français**
(auteurs `G. COSTANTINI`, `Jérôme ONILLON`) et non du programme sénégalais — ce
qui rejoint la question des droits d'usage du corpus.

**V7 est le seul qui bloque une mise en production.** Le frontend Next.js est
prêt et vérifié de bout en bout, mais le déploiement pointe encore vers le Vue.
Cinq fichiers sont à reprendre (`Dockerfile.render`, `render.yaml`, les deux
`docker-compose`, le `Makefile`), avec une différence de nature : le Vue est
**statique**, Next a besoin d'un **processus Node**.

### Trois chantiers qui demandent une contribution humaine

- **Le jeu d'évaluation de recherche** (P1.4) — 30 à 50 vraies questions
  d'élèves avec le chapitre attendu. Sans lui, impossible de prouver que le
  re-ranker du M2 améliore les réponses. Le plan le désigne comme *« le point le
  plus important »*. Il faut un enseignant, ou les questions réellement posées.
- **L'ingestion des 103 PDF vers Qdrant** (P1.3) — le pipeline fonctionne et a
  été vérifié de bout en bout (6 007 morceaux produits), mais rien n'est indexé :
  cela suppose un serveur Qdrant et le modèle d'embeddings BGE-M3, tous deux
  absents de cette machine.
- **L'archivage de `nuru-binta`** en lecture seule, avec un `README` renvoyant
  ici. Cette action appartient à son propriétaire.

---

## 6. Règles de travail à garder en tête

Ce sont celles suivies pendant toute la fusion ; les abandonner ferait perdre la
cohérence de l'ensemble.

1. **Un module à la fois**, jamais de fusion en bloc.
2. **Après chaque module** : la suite de tests passe, et le nombre de tests ne
   diminue jamais.
3. **Les tests unitaires ne suffisent pas.** Chaque module a été vérifié contre
   l'infrastructure réelle (les 103 PDF, PostgreSQL). C'est ainsi — et jamais
   par les tests seuls — qu'ont été trouvés les quatre défauts du §7.
4. **Documenter au fur et à mesure** dans `JOURNAL_FUSION.md`, en langage
   simple : ce qui est gardé, retiré, ajouté, et l'impact.
5. **Ne rien trancher seul** sur un point non prévu par le plan : l'ajouter aux
   « ⚠️ Points à valider » avec les options et un avis argumenté.
6. **Ne jamais toucher aux conteneurs Docker** qui ne nous appartiennent pas.

---

## 7. Pièges déjà rencontrés (éviter de les re-découvrir)

**Défauts trouvés uniquement par vérification sur infrastructure réelle** — ni
les tests unitaires, ni le typage, ni le build ne les auraient révélés :

1. **Trois défauts de sécurité.** Une faille d'accès parent/enseignant que
   *nous avions nous-mêmes introduite* au M3 en étendant les rôles (un parent
   pouvait consulter n'importe quel élève), refermée au M5 par une règle d'accès
   écrite une seule fois ; plus deux venant de NURU — des routes sans
   authentification, et la bonne réponse d'un quiz qui descendait dans le
   navigateur.
2. **Erreur de classement cours/TD** : la règle de découpage structurel seule
   aurait présenté **1 922 morceaux de TD sur 2 564 (74 %)** comme du cours. La
   règle retenue (découpage **+** nature du fichier source) ramène ce chiffre à
   0. Un TD ne fournit jamais de cours principal, même quand il commence par des
   « rappels de cours ».
3. **`zip()` sans garde** à l'indexation : des morceaux restaient non indexés en
   silence.
4. **La garde de route du frontend Next.js interceptait `/health`** et le
   redirigeait vers le login, mettant le tableau de bord d'administration en
   erreur.

**Pièges d'environnement** :

5. `EMBEDDING_BACKEND=bg_m3` (typo) → `ValidationError` Pydantic, l'app ne
   démarre pas. Valeur correcte : `bge_m3`.
6. `VECTOR_BACKEND=qdrant` sans Qdrant lancé → l'API plante au démarrage (pas de
   repli gracieux, contrairement à Redis).
7. `make worker` sans Redis → échec attendu (ARQ exige Redis pour démarrer).
8. Séries `"S"`/`"LS"` (au lieu de `S1`-`S5`/`L1a`-`LA`) ne matchent aucun alias
   de la taxonomie — le filtrage RAG par série échoue **silencieusement**.
9. Changer `VECTOR_BACKEND` en cours de route (memory ↔ qdrant) rend orphelins
   les documents déjà `indexed` — c'est ce que la détection `verify-all` signale.
10. Lancer `pytest` depuis la racine du dépôt fait échouer ~26 tests en cascade
    (config/env introuvables depuis ce répertoire). Toujours lancer **depuis
    `agent-tuteur-api/`**.
11. Un `.venv` créé pendant qu'un environnement conda est actif provoque des
    `Segmentation fault` sur des modules natifs. Voir `GUIDE_LANCEMENT.md` §10.
12. **`numpy==2.5.1`** ne s'installe pas sous Python 3.11 alors que les autres
    travaux de CI tournent en 3.12 : un épinglage valable seulement en 3.12
    cassait l'image Docker sans que rien ne le signale. D'où le travail
    `image-api` dans la CI.
