# Comparatif d'architectures — `rag-agent-pedagogie` vs `nuru-binta`

> **📁 Archive — plan d'origine, exécuté depuis.**
>
> Ce document décrit les deux dépôts **avant** la fusion, et propose le plan qui
> a servi à la mener. Ce plan **a été exécuté** : les huit phases sont traitées
> et fusionnées dans `main` (2026-08-06). Le document est conservé pour la trace
> du raisonnement et de l'état des lieux d'origine — **il n'est plus mis à jour**
> et son présent est celui du 31 juillet 2026.
>
> Pour l'état réel : [`STATUS.md`](STATUS.md). Pour ce qui a été fait et pourquoi,
> module par module : [`../JOURNAL_FUSION.md`](../JOURNAL_FUSION.md). Pour la
> version courte : [`RAPPORT_FUSION.md`](RAPPORT_FUSION.md).
>
> ⚠️ Toutes les recommandations n'ont pas survécu à la mesure. Exemple : le plan
> recommandait le frontend Next.js de NURU ; la mesure a montré qu'il appelait 14
> endpoints dont **2 seulement existaient**, sans aucun streaming. Next.js a été
> maintenu, mais en connaissance de cause et au prix d'un vrai portage.

*Analyse factuelle réalisée le 2026-07-31 par lecture exhaustive du code des deux
dépôts et exécution réelle des deux suites de tests. Toute affirmation chiffrée
ci-dessous est vérifiable par la commande indiquée en annexe.*

**Conventions de nommage dans ce document**

| Sigle | Dépôt | Nom applicatif |
|---|---|---|
| **ATS** | `~/nuru/rag-agent-pedagogie` (dépôt courant) | Agent Tuteur Sénégal |
| **NURU** | `~/nuru/nuru-binta` | NURU — Agent Tuteur IA |

---

## 0. Méthode et périmètre de l'analyse

Ce qui a été inspecté :

- arborescence complète des deux dépôts (hors `node_modules`, `venv`, `.next`, `dist`) ;
- l'intégralité du cœur métier des deux backends (agents, RAG, persistance, API) ;
- les deux frontends (structure, routage, client HTTP, gestion d'état, auth) ;
- la configuration, les Dockerfile / compose, les scripts de lancement ;
- l'hygiène Git (fichiers suivis, taille du dépôt, secrets) ;
- **exécution réelle des deux suites de tests** (résultats §1.3 et §2.3).

Ce qui **n'a pas** été vérifié, et doit donc être considéré comme non prouvé :

- la qualité pédagogique effective des réponses des deux agents sur le corpus réel
  (aucune évaluation RAG comparative n'a été lancée — voir §7, phase P1) ;
- le rendu visuel des deux frontends dans un navigateur ;
- les performances sous charge.

---

## 1. État des lieux — ATS (`rag-agent-pedagogie`)

### 1.1 Backend

**Volumétrie** : 6 386 lignes de Python dans `agent-tuteur-api/src/`, 2 592 lignes
de tests, 20 endpoints HTTP.

**Structuration.** Packaging `pyproject.toml` avec layout `src/` et *extras*
optionnels (`embeddings`, `vectorstore`, `persistence`, `api`, `worker`, `dev`).
Architecture hexagonale explicite : le cœur (`agent/`, `vectorstore/`,
`ingestion/`, `tools/`, `config/`, `domain/`) ne dépend ni de FastAPI ni de
SQLAlchemy ; `api/`, `workers/` et `persistence/` sont aux extrémités. Les
dépendances externes sont déclarées par **protocoles** (`agent/ports.py` :
`StudentMemoryPort`, `AuditLogPort`) avec adaptateurs in-memory pour les tests.
Composition root unique dans `factory.py`.

**Agent.** Graphe LangGraph **asynchrone** (`agent/graph.py`, 900 lignes) :

```
START → detect_intent → retrieve_context → ┬─ [exercice] detect_frustration → diagnose_hint_level → route_tool → guardrail ─┐
                                           └─ [cours]    course_planner → guardrail_course ───────────────────────────────┴→ compose_response → END
```

Deux graphes compilés partagent les mêmes fonctions de nœud : le graphe *complet*
(a→f) pour les appels non streamés, le graphe de *préparation* (a→e) pour l'API,
qui streame ensuite le LLM séparément en SSE. Tous les nœuds sont des coroutines
invoquées via `ainvoke` — aucune I/O ne bloque la boucle FastAPI.

Briques pédagogiques :

- **Échelle d'indices 0→4** (`hint_strategy.py`) : reformulation → rappel →
  indice ciblé → solution guidée → solution directe, avec règles d'escalade
  documentées (répétitions ≥ 2, frustration ≥ 0.5, demande explicite → saut à 4).
- **Détection de frustration** (`frustration.py`) sur répétitions + marqueurs.
- **Garde-fous** (`guardrails.py`) : `sanitize()` anti-injection de prompt appliqué
  **avant tout traitement**, `moderate()`, `clamp_hint_level()`.
- **Mode cours didactique** (`intent.py` + `course_plan.py`) : routage par
  intention avec défaut sûr `EXERCICE`, navigation `start/next/prev/goto`,
  continuité de session, sortie de secours si l'élève demande une résolution.
- **Outil SymPy** (`tools/calculator.py`) branché conditionnellement.

**RAG.** Embeddings hybrides derrière une interface commune : `LightEmbedder`
(hachage de n-grammes + poids lexicaux `log(1+tf)`, déterministe, **hors-ligne,
défaut**) ou `BGEM3Embedder` (import tardif de `FlagEmbedding`). Store :
`InMemoryVectorStore` (cosinus dense + produit scalaire sparse, fusionnés par
**RRF**) ou `QdrantVectorStore`. Filtrage par taxonomie curriculaire
(`config/taxonomy.py`) : niveau / classe / série / discipline / chapitre /
type_chunk, avec deux normalisations documentées et non triviales —
**expansion des alias de série** (« STIDD1 » atteint des chunks « T1 ») et
**clés normalisées** `<champ>_key` (« Les Suites Numériques » ≡ « Suites
Numeriques »), avec le commentaire de code indiquant qu'un filtre exact coupait
auparavant 92 % du corpus silencieusement.

Chunking **structurel, jamais par taille fixe** (`ingestion/chunking.py`) :
`##` = chapitre/compétence, `### Exercice` = exercice **indivisible** (énoncé +
indice + solution restent solidaires), mode « leçon » détecté automatiquement
(sections `##` = sous-notions), heuristique de titres numérotés en repli PDF, et
exclusion des sections d'auteur (« Métadonnées RAG ») du RAG.

**Persistance.** PostgreSQL, SQLAlchemy 2.0 déclaratif typé (`Mapped[...]`),
**asyncpg**, migrations **Alembic** (5 révisions dont `0002_enable_rls`),
`tenant_id` sur toutes les tables (dénormalisé sur `messages`/`feedback` pour
permettre des policies RLS sans jointure). Tables : `progress`, `audit_log`,
`conversations`, `messages`, `feedback`, `users`, `documents`.

**API.** FastAPI, 20 endpoints, **authentification JWT HS256 + bcrypt**
(`api/security.py` : `Principal`, `create_access_token`, `decode_access_token`),
rôles `admin`/`student` contraints en base (`CheckConstraint`), rate limiting
`slowapi`, CORS configurable, streaming **SSE** du chat, service optionnel du SPA
depuis l'API (image mono-conteneur).

**Ingestion asynchrone.** Worker **ARQ** + Redis, avec **dégradation gracieuse** :
si Redis est injoignable au démarrage, `/api/documents` retombe sur les
`BackgroundTasks` du process API sans planter (`_try_create_arq_pool`).
Détection des documents « orphelins » (marqués `indexed` mais sans vecteurs) au
démarrage et à la demande via `POST /api/documents/verify-all`.

**Observabilité.** Logging JSON structuré (`observability.py`), `trace_id` unique
par tour, chronométrage nœud par nœud (`_timed_node`), trace persistée dans
`messages.trace` et exposée dans l'espace admin.

### 1.2 Frontend (`agent-tuteur-web`)

Vue 3 + Vite 5, **JavaScript** (pas de TypeScript), Pinia, vue-router 4, axios,
`marked` + `DOMPurify` + `katex`. 2 240 lignes, 7 vues, 7 composants, 2 stores,
2 composables.

- **Auth réelle** : jeton JWT en `localStorage`, intercepteur axios qui l'injecte
  en `Authorization: Bearer`, intercepteur de réponse qui déconnecte sur 401,
  garde de route `beforeEach` avec restauration de session et contrôle du rôle
  admin.
- **Streaming SSE** implémenté via `fetch` + parser manuel (et non `EventSource`,
  justifié en commentaire : `EventSource` ne peut pas porter l'en-tête
  `Authorization`).
- **Rendu mathématique** soigné (`composables/useMarkdown.js`) : tokenisation des
  formules **avant** le parsing markdown puis réinjection **après** DOMPurify,
  pour éviter que markdown mange les `\` et `_` et que DOMPurify mutile le HTML
  KaTeX. `throwOnError: false` pour dégrader localement.
- Écrans : chat (avec sidebar de conversations, contexte curriculaire, feedback),
  progression, login ; admin : dashboard, documents (upload + suivi d'ingestion),
  recherche, logs, utilisateurs. Thème clair/sombre.
- **Aucune donnée simulée** : toutes les vues consomment l'API.

### 1.3 Tests (exécutés)

```
145 passed, 53 skipped in 4.43s
```

26 fichiers de tests. Les 53 *skipped* sont les tests exigeant un PostgreSQL réel.
Couverture répartie sur **trois couches** : unitaire (chunking, embeddings, store,
frustration, hint, intent, guardrails, calculator, normalize, observability, 18
tests sur `course_plan`), **API** (auth 10, chat 7, conversations 9, documents 11,
search/progression/feedback 8) et **persistance** (repositories 17).

### 1.4 Documentation & déploiement

- 9 **ADR** numérotées (choix PostgreSQL, Qdrant+Postgres, chaîne LLM, ARQ, SSE,
  tenant_id, format pivot, chunking structurel, JWT/rôles), `architecture.md`,
  `api.md`, `RAPPORT_TECHNIQUE.md`, `GUIDE_LANCEMENT.md`, `migration.md`,
  `STATUS.md` (point de reprise).
- `docker-compose.dev.yml` + `docker-compose.prod.yml` + nginx + scripts
  (`setup.sh`, `deploy.sh`, `backup.sh`), `Dockerfile.render` mono-conteneur +
  `render.yaml`, `Makefile`.
- **Corpus : 5 fichiers markdown d'exemple + 12 leçons pilotes** — c'est peu.

### 1.5 Hygiène Git

197 fichiers suivis, `.git` = **4 Mo**, `.gitignore` correct, aucun secret ni
artefact de build suivi.

---

## 2. État des lieux — NURU (`nuru-binta`)

### 2.1 Backend

**Volumétrie** : 7 669 lignes de Python dans `backend/`, 31 endpoints HTTP.

**Structuration.** `requirements.txt` plat (pas de packaging), imports absolus
`from backend.app...` qui imposent de lancer depuis la racine du dépôt, et un
`sys.path.insert(0, ...)` dans `api/main.py`. Beaucoup d'imports tardifs à
l'intérieur des fonctions (`chat.py`, `auth.py`, `admin.py`, `generate.py`),
utilisés comme mécanisme de découplage de fait. Découpage fonctionnel
`agents/` · `rag/` · `memory/` · `api/` · `llm/` · `tools/` clair et lisible.

**Agent.** Graphe LangGraph **synchrone** (`agents/graph.py`) :

```
START → planner → retriever → [math_tool?] → dispatch → {cours | exercices | quiz} → verifier → progression → END
```

Sept agents spécialisés + `OrchestratorAgent` (wrapper fin). Le `PlannerAgent` est
un routeur à mots-clés déterministe (pas d'appel LLM — choix explicitement
justifié en docstring). Le `VerifierAgent` fait deux contrôles **objectifs et
originaux** : détection de vocabulaire hors-programme multivariable
(« dérivées partielles », « gradient ») sur un concept mono-variable, et
vérification que le résultat SymPy calculé **apparaît littéralement** dans le
texte généré (empêche le LLM de recalculer et de se tromper).

**RAG.** Embeddings **BGE-M3 réels** via `sentence-transformers` (avec un cap
défensif à 4 000 caractères par texte, ajouté après un incident d'allocation de
8 Go documenté en commentaire). Store **Qdrant uniquement** —
`qdrant-client==1.18.0` épinglé avec justification (l'API `search()` supprimée au
profit de `query_points()` cassait silencieusement toute recherche). Création
idempotente des index payload `classe`/`serie`, et normalisation des variantes de
série au niveau du filtre Qdrant (`_series_filter_values`).

Retrieval en deux temps, **c'est l'apport pédagogique majeur du dépôt** :
`search_course_first()` sépare explicitement les documents de **cours** des
**compléments** (TD, exercices, corrigés) via `_classify_doc_type`, applique un
bonus de score fixe (`COURSE_PRIORITY_BONUS = 0.25`) aux cours, et retourne
`{course_docs, supplement_docs, has_course}`. Le `CoursAgent` refuse de générer
si `has_course` est faux et qu'aucun contexte n'existe — refus explicite plutôt
qu'hallucination.

Le reranking hybride combine le score dense Qdrant et un score **TF-IDF ajusté à
la volée sur le pool de candidats** (`TfidfVectorizer().fit_transform` par
requête).

**Ingestion.** Chaîne PDF complète et opérationnelle : `PyMuPDFAdapter` +
`NougatAdapter` (OCR mathématique, désactivé sur cette machine pour cause de
`pyarrow` non compilable, avec repli automatique documenté), `cleaners.py`,
puis trois extracteurs de métadonnées (`file_metadata`, `content_metadata`,
`metadata_merge`) et un chunker pédagogique par patterns
(Définition / Théorème / Exercice / Solution / Exemple / Chapitre) avec fusion des
petits chunks, découpe des gros, estimation de difficulté et extraction de
compétences.

**Persistance.** SQLAlchemy déclaratif **ancienne syntaxe** (`Column(...)`),
sessions **synchrones**, **`Base.metadata.create_all()`** au lieu de migrations,
et repli **SQLite** si `DATABASE_URL` est absent. Modèle de données pédagogique
**nettement plus riche** que celui d'ATS : `Student`, `Interaction`,
`ExerciseResult`, `ConceptMastery`, `Badge`, `Recommendation`, `User`,
`ParentStudent`, `Teacher`, `TeacherStudent`.

**Authentification.** `auth_service.py` : PBKDF2-HMAC-SHA256, 260 000 itérations,
sel aléatoire, comparaison en temps constant (`hmac.compare_digest`) — la
primitive est correcte. Quatre rôles (`student`/`teacher`/`parent`/`admin`),
création d'admin par inscription publique explicitement bloquée, liaisons
parent↔élève et enseignant↔élève, super-admin auto-créé.

**Mais : aucune de ces identités n'est appliquée.** `grep` sur
`backend/app/api/routes/` ne trouve **aucun** `Depends()` d'authentification,
aucun jeton, aucun en-tête `Authorization`. Conséquences vérifiables :

- `GET /admin/users` renvoie **la liste complète des comptes** (emails, rôles,
  classes) à n'importe quel appelant non authentifié ;
- `GET /admin/stats` idem ;
- `POST /auth/link-student` prend `user_id` **dans le corps de la requête** :
  n'importe qui peut se déclarer parent ou enseignant de n'importe quel élève ;
- `GET /parent/students/{parent_id}` et `GET /teacher/students/{teacher_id}`
  exposent les données de progression de tout élève dont on devine l'identifiant.

**LLM.** Gemini uniquement (`google-generativeai`). Pas de chaîne de repli : si la
clé manque, `_fallback_response()` renvoie un texte statique expliquant comment
configurer la clé — l'élève reçoit ce texte à la place d'une réponse. Deux
modèles distincts sont codés en dur selon le chemin d'appel :
`gemini-1.5-pro` (via `LLM_MODEL`) dans `llm_utils.py`, et
`gemini-3.1-pro-preview` en dur dans `routes/generate.py::_call_gemini`.

**Outils.** `math_tools.py` (SymPy, avec `detect_math_intent` et une
normalisation d'expressions en langage naturel français soignée : exposants
unicode, définitions `f(x)=`, fonctions usuelles) et **`sandbox.py`** — un
exécuteur Python restreint (whitelist de builtins, pas d'import arbitraire,
timeout dur de 5 s dans un processus séparé). C'est une brique de sécurité
sérieuse qui n'a pas d'équivalent dans ATS.

### 2.2 Frontend (`frontend/`)

Next.js 16 (App Router) + React 19 + **TypeScript** + Tailwind CSS 4 +
`framer-motion` + `lucide-react` + `react-markdown`/`remark-math`/`rehype-katex`.
6 992 lignes, **21 pages**, 9 composants.

Inventaire d'écrans nettement plus large qu'ATS : accueil, matières, cours `[id]`,
exercices `[id]`, quiz `[id]`, défis (gamification/classement), progression,
recherche, espaces enseignant et parent, et **10 pages d'administration**
(utilisateurs, centre IA, génération IA, publications, mis-en-avant, familles
pédagogiques, cibles cognitives, journal d'audit, scheduler).

Trois problèmes structurels, vérifiés :

1. **11 pages sur 21 ne font aucun appel au backend.** Les données y sont
   codées en dur dans le composant (`app/defis/page.tsx` : classement nominatif
   fictif ; `app/admin/scheduler/page.tsx` : tâches planifiées en `useState`
   initial ; les 7 autres pages admin idem). Ce sont des maquettes cliquables,
   pas des fonctionnalités.
2. **L'authentification n'est pas une authentification.** `AuthContext.tsx`
   stocke `{user, isAuthenticated}` en `localStorage`, sans jeton — l'état
   d'authentification est donc entièrement modifiable par l'utilisateur depuis la
   console. Pire, `login()` **et** `register()` ont un bloc `catch` qui, si le
   backend est injoignable, crée un compte local et **déduit le rôle de la chaîne
   de l'email** :
   ```ts
   if (email.includes('admin')) fallbackRole = 'admin';
   ```
   Il suffit de couper le réseau et de se connecter avec `admin@x.fr` pour
   obtenir l'interface d'administration.
3. **Aucun streaming.** Le chat fait un `POST` et attend la réponse complète.

Le `lib/api.ts` est en revanche propre : client typé, interfaces exportées,
gestion d'erreur homogène — mais avec des `catch` qui renvoient des données de
repli fabriquées (`fetchAdminStats` renvoie `rag_vectors_count: 2635` en dur),
ce qui masque les pannes au lieu de les signaler.

### 2.3 Tests (exécutés)

```
84 passed, 1 skipped in 12.54s
```

10 fichiers, 85 tests collectés. Couverture concentrée sur la **couche
ingestion/outils** : `test_metadata_unit` (23), `test_quiz_agent_unit` (13),
`test_math_tools_unit` (9), `test_parser_unit` (9), `test_chunker_unit` (7),
`test_planner_unit` (6), `test_qdrant_filters_unit` (6),
`test_auth_and_roles` (6), `test_quiz_state_integration` (5),
`test_integration` (1).

**Aucun test de route HTTP.** L'absence d'authentification décrite en §2.1
n'aurait donc pas pu être détectée par la suite de tests.

### 2.4 Documentation & déploiement

- `README.md` (22 Ko) et `DOCUMENTATION_TECHNIQUE.md` (93 Ko, **non suivi par
  Git** — il apparaît en `??` dans `git status`). Pas d'ADR : les décisions sont
  argumentées **dans les commentaires de code**, souvent très bien (voir
  `requirements.txt`, qui explique pourquoi `qdrant-client` et `gradio` sont
  épinglés) — mais elles ne sont pas indexées ni retrouvables.
- `Dockerfile` + `docker-compose.yml` (qdrant + postgres + backend + frontend),
  scripts `run_all.sh` / `run_api.sh` / `run_frontend.sh` / `run_ingest.sh`.
- **Corpus réel et substantiel : 106 PDF suivis par Git** (cours Terminale S1/S2,
  TD par chapitre, devoirs, compositions, bacs blancs, annales, fascicules) et
  102 documents markdown extraits. **C'est l'actif le plus précieux des deux
  dépôts réunis.**

### 2.5 Hygiène Git

1 531 fichiers suivis, `.git` = **66 Mo**, 2 commits. Sont suivis par erreur :

- **`cloudflared`** : binaire de 39 Mo (soit ~60 % du poids du dépôt) ;
- **1 121 fichiers JSON de chunks** dans `data/processed/chunks/` pour seulement
  **102 documents distincts** — soit 11 versions horodatées de chaque document,
  toutes conservées ;
- **`delete_file/`** : 15 fichiers de code mort explicitement nommé « à
  supprimer », dont l'ancien frontend Gradio et d'anciens scripts de test.

`.env` et `nuru_student_memory.db` sont, eux, correctement ignorés.

---

## 3. Éléments communs aux deux approches

| Brique | ATS | NURU | Commentaire |
|---|---|---|---|
| Langage backend | Python 3.11 | Python 3.11.9 | Convergent |
| Framework API | FastAPI + Pydantic v2 | FastAPI + Pydantic v2 | Convergent |
| Orchestration agents | LangGraph `StateGraph` | LangGraph `StateGraph` | **Convergent — fusion facilitée** |
| Base vectorielle | Qdrant (option) | Qdrant (seul) | Convergent |
| Embeddings cibles | BGE-M3 (option) | BGE-M3 (défaut) | Convergent |
| Base relationnelle | PostgreSQL | PostgreSQL (repli SQLite) | Convergent |
| ORM | SQLAlchemy | SQLAlchemy | Syntaxes différentes (§4) |
| Calcul symbolique | SymPy | SymPy | Convergent |
| Doctrine anti-hallucination | Prompt ancré RAG + garde-fous | Prompt ancré RAG + Verifier | Convergent dans l'intention |
| Rendu maths front | KaTeX | KaTeX | Convergent |
| Conteneurisation | Docker + Compose | Docker + Compose | Convergent |
| Domaine | Programme sénégalais | Programme sénégalais Terminale S1/S2 | ATS plus large (préscolaire→Bac) |
| Langue de travail | Français (code + docs) | Français (code + docs) | Convergent |

**Conclusion de cette section : les deux équipes ont convergé spontanément sur la
même pile technique.** La fusion n'est donc pas un choix de stack, mais un choix
de *qualité d'implémentation* brique par brique.

---

## 4. Divergences par brique

| Brique | ATS | NURU | Écart déterminant |
|---|---|---|---|
| **Packaging** | `pyproject.toml`, layout `src/`, extras optionnels | `requirements.txt` plat, `sys.path.insert` | ATS installable et testable hors de son répertoire |
| **Couplage** | Hexagonal, ports/protocoles, cœur sans framework | Fonctionnel, imports tardifs, `backend.app.*` absolus | ATS testable hors-ligne sans infra |
| **Asynchronisme** | Tout le graphe et l'API en `async`/`ainvoke` | Graphe et sessions DB **synchrones** | NURU bloque la boucle FastAPI sur chaque appel LLM/Qdrant |
| **Streaming** | SSE, graphe scindé a→e / f | Aucun (POST bloquant) | Perception de latence très différente pour l'élève |
| **Fusion de scores** | **RRF** (fondé sur les rangs) | Somme pondérée dense + TF-IDF ajusté par requête | RRF robuste aux échelles hétérogènes ; TF-IDF sur ~40 candidats est statistiquement faible et coûte un `fit` par requête |
| **Priorisation cours/TD** | ❌ absente | ✅ `search_course_first` + bonus de type | **Avantage NURU, à importer** |
| **Filtrage curriculaire** | Taxonomie complète + alias de série + clés normalisées | `classe`/`serie` uniquement, normalisation partielle | ATS traite un problème réel (92 % du corpus perdu) |
| **Chunking** | Structurel, exercice indivisible, mode leçon | Par patterns de section + fusion/découpe par taille | Approches complémentaires (§6.3) |
| **Parsing PDF** | `pypdf` / `python-docx` génériques | **PyMuPDF + Nougat OCR + cleaners + 3 extracteurs de métadonnées** | **Avantage NURU pour les maths** |
| **Migrations DB** | Alembic, 5 révisions, RLS | `create_all()` | ATS déployable en production sans perte de données |
| **Multi-tenant** | `tenant_id` partout + RLS PostgreSQL | Aucun | ATS prêt pour plusieurs établissements |
| **Modèle pédagogique** | `progress`, `audit_log` | **`ExerciseResult`, `ConceptMastery`, `Badge`, `Recommendation`, liaisons parent/prof** | **Avantage NURU, à importer** |
| **Quiz / évaluation** | ❌ absents | ✅ génération JSON validée + correction + maîtrise + XP + badges | **Avantage NURU, à importer** |
| **Mode cours didactique** | ✅ plan de cours navigable section par section | ✅ génération d'un chapitre complet en un bloc | Deux produits pédagogiques différents (§8, point 6) |
| **Rôles** | admin / élève | élève / enseignant / parent / admin | **Avantage NURU en couverture** |
| **Application des rôles** | JWT + `Depends` + RLS sur **toutes** les routes | **Aucune — 31 routes publiques** | **Écart le plus grave du comparatif** |
| **Chaîne LLM** | Router Mistral → Ollama → Mock, bascule silencieuse | Gemini seul, message statique en repli | ATS ne renvoie jamais une non-réponse à l'élève |
| **Sandbox d'exécution** | ❌ | ✅ processus séparé, whitelist, timeout 5 s | **Avantage NURU** (utile si tracés/calculs générés) |
| **Ingestion asynchrone** | ARQ + Redis, repli `BackgroundTasks` | Scripts CLI (`run_ingest.sh`) | ATS permet l'upload depuis l'interface |
| **Observabilité** | JSON structuré, `trace_id`, trace par nœud persistée | `basicConfig(INFO)` + `print` | ATS diagnosticable en production |
| **Configuration** | `pydantic-settings` typée, une source de vérité | `os.getenv` dispersés + défauts en dataclass | ATS échoue au démarrage sur une clé invalide plutôt que silencieusement |
| **Tests** | 145 ✅ / 53 ⏭, 3 couches dont API et persistance | 84 ✅ / 1 ⏭, unitaires ; **0 test de route** | ATS couvre les régressions d'intégration |
| **Documentation** | 9 ADR + 6 documents indexés | 115 Ko en 2 fichiers, dont 93 Ko non commités | ATS retrouvable ; NURU excellent en commentaires de code |
| **Corpus** | 5 md + 12 leçons pilotes | **106 PDF + 102 extractions du programme réel** | **Avantage NURU, décisif** |
| **Hygiène Git** | 197 fichiers, 4 Mo | 1 531 fichiers, 66 Mo (binaire 39 Mo, 1 121 JSON redondants, code mort) | ATS clonable en quelques secondes |

---

## 5. Comparatif dédié — Frontend

| Critère | ATS `agent-tuteur-web` | NURU `frontend` |
|---|---|---|
| **Framework** | Vue 3.4 + Vite 5 | Next.js 16 (App Router) + React 19 |
| **Typage** | JavaScript pur | **TypeScript** (`types/index.ts`, interfaces d'API) |
| **Styles** | CSS écrit à la main, variables de thème | **Tailwind CSS 4** + `tailwind-merge` + `clsx` |
| **Animations** | Transitions CSS | `framer-motion` |
| **Icônes** | SVG inline | `lucide-react` |
| **État global** | **Pinia** (`auth`, `chat`) | React Context (`AuthContext`) uniquement |
| **Routage** | vue-router 4 + **garde `beforeEach`** (auth + rôle) | App Router (fichiers) — **aucune garde** |
| **Client HTTP** | axios + intercepteurs (Bearer, 401 → logout) | `fetch` nu dans `lib/api.ts` |
| **Authentification** | **JWT réel**, restauration de session, expiration gérée | `localStorage` sans jeton + **repli local qui déduit le rôle admin de l'email** |
| **Streaming du chat** | **SSE via `fetch`** + parser incrémental | Aucun (POST bloquant) |
| **Rendu maths** | `marked` + tokenisation + DOMPurify + KaTeX (protocole documenté contre les fuites de caractères) | `react-markdown` + `remark-math` + `rehype-katex` (standard, plus simple) |
| **Volume** | 2 240 lignes, 7 vues | 6 992 lignes, **21 pages** |
| **Écrans câblés au backend** | **7 / 7 (100 %)** | **10 / 21 (48 %)** |
| **Écrans en données figées** | 0 | **11** (défis, progression, matières/maths, 8 pages admin) |
| **Gamification** | Absente | Badges, XP, classement (maquette) |
| **Espaces enseignant / parent** | Absents | Présents (partiellement câblés) |
| **Découpage du bundle** | Lazy imports par route (`() => import(...)`) | Automatique par route (App Router) |
| **Build suivi par Git** | `dist/` ignoré ✅ | `.next/` ignoré ✅ |

**Lecture.** Les deux frontends sont *complémentaires et inversés* : NURU a la
**vision produit** (21 écrans, design system moderne, TypeScript, gamification,
espaces enseignant/parent) mais **aucune infrastructure fonctionnelle** (pas de
jeton, pas de garde, pas de streaming, la moitié des écrans en carton-pâte). ATS
a **l'infrastructure complète et correcte** mais un périmètre fonctionnel étroit
et une dette de typage (JavaScript pur sur un contrat d'API de 20 endpoints).

---

## 6. Évaluation argumentée, brique par brique

Pour chaque brique : la base retenue, et **pourquoi** (critères : lisibilité,
performance, maintenabilité, extensibilité, conventions modernes).

### 6.1 Architecture générale → **ATS**

**Justification.** Le critère décisif est le coût d'ajout d'un module futur.
Dans ATS, ajouter un backend LLM = implémenter `BaseLLM` et l'ajouter à
`build_router` ; ajouter un store = implémenter `BaseVectorStore` ; ajouter une
persistance = implémenter le protocole `StudentMemoryPort`. Aucune de ces
opérations ne touche au graphe de l'agent. Dans NURU, le client Gemini est importé
nominativement dans `llm_utils.get_llm()`, le retriever est instancié
directement dans `containers.py` et dans `generate.py`, et `chat.py` importe
`EvaluationAgent`/`ProgressionAgent` à l'intérieur des fonctions : chaque ajout
implique de toucher plusieurs points d'appel.

S'ajoute un critère opérationnel : ATS **démarre sans aucune infrastructure**
(`EMBEDDING_BACKEND=light`, `VECTOR_BACKEND=memory`, `LLM_BACKEND=mock`), ce qui
rend les 145 tests exécutables en 4 secondes. NURU exige Qdrant en ligne et
charge BGE-M3 (~2 Go) pour la moindre recherche.

### 6.2 Pipeline RAG — recherche → **ATS comme base, avec un apport NURU obligatoire**

**Base ATS**, pour trois raisons techniques :

1. **RRF plutôt que somme pondérée.** Additionner un cosinus dense (∈ [0,1],
   distribution resserrée autour de 0.40–0.50 sur ce corpus, comme le note le
   commentaire de `config.py` de NURU) et une similarité TF-IDF (échelle et
   distribution totalement différentes) avec des poids fixes (0.6 / 0.4) donne un
   classement dont le comportement dépend du corpus. RRF ne combine que des
   **rangs** — c'est précisément le problème qu'il résout, et c'est la pratique
   de référence pour la recherche hybride.
2. **Coût par requête.** NURU appelle `TfidfVectorizer().fit_transform()` sur les
   textes candidats **à chaque recherche**. L'IDF est donc calculé sur ~40
   documents, ce qui n'a guère de sens statistique, pour un coût CPU non nul à
   chaque question d'élève. ATS calcule les poids sparse **une fois à
   l'indexation**.
3. **Filtrage curriculaire.** ATS filtre sur 6 champs avec expansion des alias de
   série et clés normalisées ; NURU sur 2 champs. Le commentaire de
   `taxonomy.py` documente un incident réel où un filtre exact coupait 92 % du
   corpus — c'est exactement le type de bug que NURU n'a pas encore rencontré
   parce qu'il ne filtre presque pas.

**Apport NURU à importer impérativement** : la **priorisation cours / complément**
(`search_course_first`, `_classify_doc_type`, `has_course`). C'est une idée
pédagogique juste que ATS n'a pas : sur un corpus réel constitué majoritairement
de TD et d'annales (ce qui est le cas des 106 PDF), une recherche purement
sémantique remonte des exercices là où l'élève demande un cours. Le refus
explicite de générer quand `has_course` est faux est également à reprendre.

**À ne pas reprendre** : le `score_threshold = 0.30` de `VectorIndexerConfig` —
il est défini mais **jamais lu nulle part dans le code** (vérifié par `grep`).
C'est de la configuration morte, à supprimer ou à implémenter.

### 6.3 Pipeline RAG — ingestion et chunking → **ATS comme base, parsing PDF de NURU**

**Chunking : base ATS.** Le principe « un chunk = une unité pédagogique
complète, l'exercice est indivisible » est plus juste que « découper aux
patterns puis fusionner/découper par taille ». Concrètement, `_split_large_chunks`
de NURU coupe un chunk de plus de 1 500 caractères sur les paragraphes : un
exercice long est donc séparé de son corrigé, et le RAG peut remonter l'énoncé
sans la solution. ATS garde le trio solidaire par construction. ATS gère aussi le
format « leçon » et exclut les sections d'auteur du RAG.

**Parsing : import de NURU.** ATS extrait le PDF via `pypdf`, qui perd la
structure et massacre les formules. NURU a construit la chaîne adaptée au corpus
mathématique : `PyMuPDFAdapter` avec repli, `NougatAdapter` (OCR spécialisé
formules), `cleaners.py`, et trois extracteurs de métadonnées avec fusion. Ces
modules s'insèrent derrière l'interface `ingestion/loaders.extract_text` d'ATS
sans toucher au reste du pipeline. **Les 23 tests de `test_metadata_unit` et les
9 de `test_parser_unit` se transposent avec eux.**

### 6.4 Gestion des données / persistance → **ATS pour l'infrastructure, NURU pour le modèle métier**

**Infrastructure : ATS, sans hésitation.**

- **Alembic vs `create_all()`** : `create_all()` ne crée que les tables absentes
  et **ne modifie jamais une table existante**. Toute évolution de schéma après
  la première mise en production impose une intervention manuelle ou une perte de
  données. C'est éliminatoire pour un produit destiné à des établissements.
- **Async vs sync** : les sessions synchrones de NURU appelées depuis des routes
  `async def` bloquent la boucle d'événements ; sous charge, l'API se sérialise.
- **SQLAlchemy 2.0 typé (`Mapped[str]`) vs 1.x (`Column(String)`)** : le premier
  est vérifiable statiquement, le second non.
- **RLS + `tenant_id`** : ATS peut héberger plusieurs établissements sur une
  instance ; NURU non, et l'ajouter après coup impose de toucher toutes les
  tables et toutes les requêtes.

**Modèle métier : NURU, largement.** `ExerciseResult` (score, difficulté, détail
JSON), `ConceptMastery` (score de maîtrise, tentatives, réussites — vrai *mastery
learning*), `Badge`, `Recommendation`, `ParentStudent` : ATS n'a rien
d'équivalent (`progress` ne stocke qu'un `hint_level` et une `competence`). Ces
tables doivent être **portées** sur les conventions ATS (UUID, `tenant_id`,
`Mapped[...]`, migration Alembic), pas copiées telles quelles.

**À abandonner du modèle NURU** : la table `Teacher` (avec son propre
`password_hash`) **doublonne** `User(role='teacher')`, et les routes
`POST /teacher/register` / `POST /teacher/login` doublonnent `/auth/register` et
`/auth/login`. Deux chemins d'authentification pour la même population, c'est une
source de divergence garantie. Une seule table `users` avec un rôle.

### 6.5 API → **ATS, de façon non négociable**

**Justification.** Ce n'est pas une préférence d'architecture, c'est une question
de recevabilité du produit. NURU expose 31 routes sans aucun contrôle d'accès,
dont l'annuaire complet des utilisateurs et les données de progression nominatives
de mineurs. Le travail d'authentification **existe** dans `auth_service.py` (et il
est bien fait), mais il n'est **jamais branché** sur les routes.

ATS apporte, déjà en place et testé (10 tests sur `auth`) : JWT HS256 signé
portant `tenant_id`/`role`/`student_id`, bcrypt, `Principal` injecté par
`Depends`, rôle contraint en base, RLS PostgreSQL en défense en profondeur, rate
limiting par endpoint, et SSE pour le chat.

**Apport NURU à importer** : le *périmètre fonctionnel* des routes — évaluation
(`/evaluation/quiz`, `/evaluation/exercice`), tableau de bord élève
(`/student/dashboard`), suivi enseignant (`/teacher/class-stats`), suivi parent.
Ces endpoints répondent à des besoins réels absents d'ATS ; ils doivent être
réécrits derrière les dépendances d'authentification.

### 6.6 Agents pédagogiques → **ATS pour l'ossature, NURU pour trois briques**

**Ossature ATS** : graphe async, deux graphes compilés pour le streaming,
`node_trace` chronométré, ports injectables par requête (un seul `TutorAgent`
sert toutes les requêtes concurrentes sans état partagé — NURU utilise un
singleton `_orchestrator` global avec des agents instanciés une fois, et un
dictionnaire `sessions = {}` en mémoire de module, qui ne survit ni au
redémarrage ni au multi-worker).

L'échelle d'indices 0→4 d'ATS avec escalade sur frustration/répétitions est plus
fine et **testée** (7 tests) que les 5 niveaux de NURU pilotés par un simple
compteur d'itérations. `sanitize()` anti-injection appliqué en tout premier n'a
pas d'équivalent chez NURU.

**Trois briques NURU à importer :**

1. **`QuizAgent`** — génération JSON avec réessais, parsing tolérant aux
   ```` ```json ````, et **rejet explicite du contenu placeholder** : si le LLM
   ne produit pas de quiz valide après *N* tentatives, l'agent renvoie une
   absence propre plutôt qu'un faux quiz. 13 tests. ATS n'a aucun quiz.
2. **`EvaluationAgent` + `ProgressionAgent`** — correction, calcul de maîtrise,
   attribution de badges, recommandations. ATS n'a aucune boucle d'évaluation.
3. **Les deux contrôles objectifs du `VerifierAgent`** —
   `_check_mathematical_consistency` : vocabulaire hors-programme multivariable,
   et présence littérale du résultat SymPy dans le texte généré. Ce sont des
   vérifications **déterministes et bon marché** (pas de second appel LLM) qui
   attrapent une classe d'hallucinations réelle.

**À ne pas importer** : `_check_coherence` (score fondé sur la présence de
« donc », « ainsi », « en effet » — heuristique sans fondement, dont le code de
NURU reconnaît lui-même en commentaire qu'elle est « peu fiable pour de courtes
réponses ») et `_check_hallucinations` (détection de « je pense », « peut-être »
— mesure la prudence rhétorique, pas la véracité).

### 6.7 Frontend → **Next.js/TypeScript de NURU comme cible, couche données d'ATS réécrite**

**Recommandation : migrer vers Next.js + TypeScript**, en reprenant le design
system et l'inventaire d'écrans de NURU, et en **réécrivant intégralement la
couche données**.

**Justification.**

- **Le typage est le gain décisif.** Le contrat d'API atteindra 30+ endpoints
  après fusion. En Vue/JavaScript pur, chaque renommage de champ côté API se
  découvre à l'exécution ; en TypeScript avec des types générés depuis le schéma
  OpenAPI de FastAPI, il se découvre à la compilation. Sur un projet à deux
  développeurs qui viennent de constater qu'ils ont divergé, c'est le mécanisme
  de coordination le moins coûteux.
- **Le travail d'interface est le poste le plus lourd, et il est déjà fait à
  moitié.** NURU a 21 écrans conçus ; ATS en a 7. Repartir de Vue signifie
  concevoir et coder 14 écrans supplémentaires ; repartir de Next.js signifie
  recâbler 11 écrans existants. Le second chantier est plus mécanique et plus
  prévisible.
- **Tailwind 4 + App Router + React 19** sont les conventions dominantes de 2026 ;
  le CSS écrit à la main d'ATS (`App.vue` contient les variables de thème, les
  boutons, les badges…) est un design system artisanal qui devra de toute façon
  être formalisé.

**Ce qu'il faut impérativement porter d'ATS vers le frontend cible** (sans quoi la
migration est une régression) :

1. le **jeton JWT** et son cycle de vie (injection `Bearer`, 401 → déconnexion,
   restauration de session) ;
2. la **garde de route** par authentification et par rôle (`middleware.ts` en
   App Router) ;
3. le **streaming SSE** du chat via `fetch` + parser incrémental ;
4. le **protocole de rendu markdown + KaTeX** d'ATS *si* `rehype-katex` s'avère
   insuffisant sur les sorties réelles du LLM (à tester : `remark-math` gère mal
   certains délimiteurs `\(...\)` que Mistral émet).

**Ce qu'il faut supprimer de NURU avant toute reprise** :

- le repli local de `AuthContext` (faille d'élévation de privilège) ;
- tous les `catch` de `lib/api.ts` qui renvoient des données fabriquées ;
- les 11 pages non câblées — soit les brancher, soit les retirer du menu. Une
  maquette laissée dans la navigation devient une promesse non tenue en démo.

**Alternative si l'équipe n'a pas les compétences React** : conserver Vue 3, y
ajouter TypeScript, et reprendre uniquement l'*inventaire d'écrans* et le
*parcours utilisateur* de NURU. C'est le point 1 à trancher en réunion (§8).

### 6.8 Tests → **ATS**

145 vs 84, mais surtout **trois couches vs une**. NURU teste très bien ce qu'il
teste (23 tests sur l'extraction de métadonnées, 13 sur le quiz), mais n'a
**aucun test de route HTTP** — c'est structurellement pour cela que 31 endpoints
non authentifiés ont pu être livrés sans que rien ne signale l'anomalie. ATS a
45 tests d'API et 22 de persistance.

Stratégie cible : **conserver les deux suites**. Les tests unitaires de NURU sur
parsing/métadonnées/chunker/math_tools/quiz sont directement réutilisables et
couvrent des modules qu'ATS n'a pas.

### 6.9 Configuration & déploiement → **ATS**

- **Configuration** : `pydantic-settings` typée avec `Literal` sur les backends
  (une valeur invalide fait échouer le démarrage avec un message explicite — c'est
  documenté comme piège rencontré dans `STATUS.md`) vs `os.getenv` dispersés,
  défauts en dataclass, et `load_dotenv` dans `api/main.py` avec un
  `sys.path.insert`.
- **Déploiement** : compose dev **et** prod, nginx frontal avec SSL et rate
  limiting, étape `migrate` explicite, scripts de sauvegarde, image
  mono-conteneur + blueprint Render pour la démo publique. NURU : un compose de
  développement et des scripts shell.
- **Reproductibilité** : NURU a un vrai réflexe d'épinglage justifié
  (`qdrant-client==1.18.0`, `gradio==6.20.0`, avec l'incident documenté en
  commentaire) — c'est une bonne pratique **à conserver** dans le dépôt cible, où
  les bornes sont pour l'instant des `>=` non verrouillés.

### 6.10 Sécurité → **ATS**, avec un apport NURU

ATS : JWT, bcrypt, RLS, rate limiting, sanitisation anti-injection de prompt,
modération, aucun secret suivi par Git.
NURU : primitive PBKDF2 correcte mais jamais appliquée, 31 routes ouvertes, faille
d'élévation de privilège côté frontend, `cloudflared` commité.

**Apport NURU** : `tools/sandbox.py` (processus séparé, whitelist de builtins,
timeout 5 s). Nécessaire **uniquement** si l'on conserve la génération de tracés
ou l'exécution de calculs produits par le LLM — à décider (§8, point 6).

### 6.11 Actif de données → **NURU, sans équivalent**

106 PDF du programme réel (cours Terminale S1/S2, TD par chapitre, devoirs,
compositions, bacs blancs, annales, fascicules) contre 5 markdown d'exemple et 12
leçons pilotes. **Cet actif justifie à lui seul la fusion** : ATS est une
mécanique sans carburant, NURU a le carburant.

---

## 7. Plan de fusion / consolidation

**Architecture cible retenue : le dépôt ATS comme base structurelle, enrichi des
briques métier, du corpus et du frontend de NURU.**

Voir le schéma et les extraits de code d'illustration dans
[`ARCHITECTURE_CIBLE.md`](ARCHITECTURE_CIBLE.md).

### 7.1 Synthèse : repris / adapté / abandonné

| Origine | Élément | Décision | Justification |
|---|---|---|---|
| ATS | Cœur hexagonal, ports, `factory.py` | **Repris tel quel** | Coût d'extension minimal, testable hors-ligne |
| ATS | Graphe LangGraph async + double compilation SSE | **Repris tel quel** | Streaming et non-blocage acquis |
| ATS | Indices 0→4, frustration, guardrails, intent, course_plan | **Repris tel quel** | Testés (48 tests), sans équivalent NURU |
| ATS | Taxonomie, RRF, store abstrait, chunking structurel | **Repris tel quel** | Voir §6.2, §6.3 |
| ATS | Persistance async + Alembic + RLS + `tenant_id` | **Repris tel quel** | Voir §6.4 |
| ATS | JWT, bcrypt, `Principal`, rate limiting, SSE | **Repris tel quel** | Voir §6.5 |
| ATS | ARQ + repli `BackgroundTasks`, détection d'orphelins | **Repris tel quel** | Upload depuis l'interface |
| ATS | Observabilité JSON, `trace_id`, `node_trace` | **Repris tel quel** | Diagnostic en production |
| ATS | 9 ADR, compose dev/prod, Makefile, Render | **Repris tel quel** | Voir §6.9 |
| NURU | **Corpus 106 PDF + 102 extractions** | **Repris tel quel** (hors Git — §7.2 P0) | Actif irremplaçable |
| NURU | `PyMuPDFAdapter`, `NougatAdapter`, `cleaners`, 3 extracteurs de métadonnées | **Adapté** (derrière `ingestion/loaders`) | Parsing math que `pypdf` ne sait pas faire |
| NURU | `search_course_first`, `_classify_doc_type`, `has_course` | **Adapté** (re-ranker au-dessus du RRF, pas à la place) | Priorisation cours/TD indispensable sur ce corpus |
| NURU | `math_tools.detect_math_intent` + normalisation FR | **Adapté** (fusion avec `tools/calculator.py`) | Plus riche que l'existant ATS |
| NURU | `sandbox.py` | **Repris tel quel** *si* exécution de code conservée | Voir §8 point 6 |
| NURU | `ExerciseResult`, `ConceptMastery`, `Badge`, `Recommendation`, `ParentStudent` | **Adapté** (UUID + `tenant_id` + `Mapped[]` + Alembic) | Modèle *mastery learning* absent d'ATS |
| NURU | `QuizAgent`, `EvaluationAgent`, `ProgressionAgent` | **Adapté** (async + ports + nœuds du graphe ATS) | Boucle d'évaluation absente d'ATS |
| NURU | `VerifierAgent._check_mathematical_consistency` | **Repris tel quel** | Contrôles déterministes utiles |
| NURU | Rôles `teacher` / `parent` + liaisons | **Adapté** (dans `users.role` + JWT + RLS) | Périmètre produit |
| NURU | Design system, 21 écrans, TypeScript, Tailwind | **Adapté** (couche données réécrite) | Voir §6.7 |
| NURU | Tests unitaires parser / métadonnées / chunker / math / quiz | **Repris tel quel** | 58 tests directement réutilisables |
| NURU | Épinglage justifié des versions critiques | **Repris** (à appliquer au `pyproject.toml` cible) | Reproductibilité |
| NURU | Table `Teacher` + `/teacher/register` + `/teacher/login` | **Abandonné** | Doublonne `User(role='teacher')` et `/auth/*` |
| NURU | `create_all()`, repli SQLite par défaut | **Abandonné** | Pas d'évolution de schéma possible |
| NURU | `sys.path.insert`, imports `backend.app.*` absolus | **Abandonné** | Remplacés par le packaging `src/` |
| NURU | Reranking TF-IDF ajusté par requête, `score_threshold` mort | **Abandonné** | Superseded par RRF ; configuration jamais lue |
| NURU | `POST /chat/simple` (debug) | **Abandonné** | Chemin de code parallèle non testé |
| NURU | `AuthContext` avec repli local de connexion | **Abandonné** | Élévation de privilège |
| NURU | Les 11 pages à données figées, `lib/mockData.ts` | **Abandonné** ou câblé | Pas de maquette en production |
| NURU | `cloudflared` (39 Mo), 1 121 JSON redondants, `delete_file/` | **Abandonné** | Hygiène Git |
| NURU | `_check_coherence`, `_check_hallucinations` | **Abandonné** | Heuristiques sans fondement (§6.6) |
| ATS | Corpus d'exemple (5 md) | **Conservé** en fixtures de test uniquement | Remplacé par le corpus NURU en production |

### 7.2 Étapes de migration, dans l'ordre

> Les durées sont indicatives, pour deux développeurs à temps partiel. Chaque
> phase se termine par « la suite de tests passe » — jamais autrement.

**P0 — Décision et gel (0,5 j).**
1. Valider en réunion l'architecture cible et les 8 points du §8.
2. Geler les développements fonctionnels dans les deux dépôts.
3. **Sortir le corpus de Git NURU** : les 106 PDF vont dans un stockage objet
   (MinIO/S3) ou Git LFS ; `cloudflared`, `data/processed/chunks/` et
   `delete_file/` sont retirés du suivi. Le dépôt cible reste sous 10 Mo.
4. Créer la branche `feat/fusion` sur ATS.

**P1 — Données et mesure (3–5 j). *Prioritaire : c'est ce qui dé-risque tout le reste.***
1. Porter les adaptateurs de parsing de NURU derrière `ingestion/loaders.py`
   d'ATS (`PyMuPDFAdapter`, `NougatAdapter` optionnel, `cleaners`).
2. Porter les 3 extracteurs de métadonnées ; les mapper sur la taxonomie ATS
   (`niveau`/`classe`/`serie`/`discipline`/`chapitre`/`type_chunk`).
3. Ingérer les 106 PDF via le pipeline ATS complet vers Qdrant.
4. **Construire un jeu d'évaluation de recherche** : 30 à 50 questions d'élèves
   réelles avec le chapitre attendu, et mesurer `recall@5` **avant** toute
   optimisation. Sans cette mesure, les décisions de §7.2/P2 sont des opinions.
5. Reprendre les 58 tests unitaires NURU concernés.

**P2 — RAG : priorisation pédagogique (2–3 j).**
1. Ajouter `type_chunk` = `cours` / `complement` à l'annotation
   (`ingestion/annotation.py`), dérivé du chemin source (`raw/cours` vs
   `raw/exercices`) et des patterns de NURU.
2. Implémenter un re-ranker **au-dessus** du RRF (et non à sa place) : bonus de
   type + séparation `course_docs` / `supplement_docs` / `has_course`, exposés au
   nœud `guardrail`/`guardrail_course`.
3. Reprendre le refus explicite de générer quand `has_course` est faux.
4. Re-mesurer `recall@5` et le taux de « cours en tête » ; conserver le
   re-ranker seulement s'il améliore la seconde métrique sans dégrader la première.

**P3 — Domaine pédagogique (5–8 j).**
1. Migration Alembic `0006_pedagogical_progress` : `exercise_results`,
   `concept_mastery`, `badges`, `recommendations`, `student_links` — conventions
   ATS (UUID, `tenant_id`, `Mapped[]`, RLS).
2. Étendre `users.role` à `('admin','teacher','parent','student')`
   (migration `0007_extend_roles`) et propager dans le `Principal` JWT.
3. Porter `EvaluationAgent` et `ProgressionAgent` en `async`, derrière de
   nouveaux ports (`EvaluationPort`, `MasteryPort`) sur le modèle de
   `agent/ports.py`.
4. Porter `QuizAgent` comme **nouvelle branche du graphe** ATS
   (`detect_intent` → `Intent.QUIZ`), avec sa validation JSON et son rejet du
   placeholder.
5. Ajouter `VerifierAgent._check_mathematical_consistency` en nœud terminal
   optionnel du graphe.

**P4 — API (3–5 j).**
1. Nouveaux routeurs `quiz`, `evaluation`, `teacher`, `parent`, extension de
   `progression` — **tous** derrière `Depends(get_current_principal)` et les
   contrôles de rôle.
2. Règle d'accès : un parent ou un enseignant ne voit un élève **que** via une
   ligne `student_links` le liant, vérifiée côté serveur — jamais via un
   identifiant fourni dans le corps de la requête.
3. Tests d'API pour chacune (modèle : `tests/api/test_auth.py`), **dont un test
   négatif 401/403 par route**. C'est le garde-fou qui manquait à NURU.
4. Regénérer le schéma OpenAPI (il servira de source aux types du frontend).

**P5 — Frontend (10–15 j, dépend du point 1 de §8).**
1. Nouveau projet Next.js/TS dans `agent-tuteur-web-next/`, design system et
   composants repris de NURU.
2. Client API **typé, généré depuis OpenAPI** ; suppression de tous les replis
   de données fabriquées.
3. Portage des acquis ATS : JWT + `middleware.ts` (garde auth/rôle) + streaming
   SSE + rendu KaTeX.
4. Écrans dans l'ordre : login → chat → progression → admin documents → admin
   utilisateurs → quiz/évaluation → enseignant → parent → gamification.
5. Suppression des écrans non câblés restants ; bascule et retrait de
   `agent-tuteur-web/`.

**P6 — LLM (1–2 j).**
1. Ajouter `GeminiLLM(BaseLLM)` à `agent/llm/`, et l'intégrer à `build_router`
   avec un ordre configurable (`LLM_BACKEND`, `LLM_CHAIN`).
2. Supprimer le modèle codé en dur (`gemini-3.1-pro-preview`) : une seule source
   de vérité de configuration.
3. Tests de bascule sur le modèle de `test_llm_fallback.py` (6 tests existants).

**P7 — Consolidation (2–3 j).**
1. ADR de la fusion : `0010-fusion-nuru-ats.md` (pourquoi cette base, quels
   apports, quels abandons).
2. Fusion des documentations ; le contenu utile de `DOCUMENTATION_TECHNIQUE.md`
   est réparti dans `architecture.md` / `api.md` / ADR — pas recopié en bloc.
3. Épinglage des versions critiques dans `pyproject.toml` (réflexe NURU).
4. CI : `pytest` + `ruff` + `npm run build` sur chaque PR. **C'est la garantie
   que la divergence ne se reproduira pas.**
5. Archivage du dépôt `nuru-binta` en lecture seule, avec un `README` pointant
   vers le dépôt cible.

### 7.3 Chemin critique et parallélisation

```
P0 ──┬── P1 ── P2 ─────────────┐
     │                          ├── P4 ── P5 ── P7
     └── P3 (dépend de P0 seul) ┘
          P6 en parallèle de P3/P4
```

P1 et P3 sont indépendants : un développeur peut prendre les données/RAG pendant
que l'autre prend le domaine pédagogique. P5 est le poste le plus long — il doit
démarrer dès que le schéma OpenAPI de P4 est stable, pas après.

---

## 8. Points à trancher collectivement

Repris et développés dans [`SYNTHESE_REUNION_TECHNIQUE.md`](SYNTHESE_REUNION_TECHNIQUE.md).

1. **Frontend cible** : Next.js/TypeScript (recommandé) ou Vue 3 conservé ?
2. **LLM principal** : Gemini ou Mistral en tête de chaîne ?
3. **Corpus** : droits d'usage des 106 PDF, et stockage (Git LFS vs objet) ?
4. **Périmètre v1** : les rôles enseignant et parent sont-ils dans la v1 ?
5. **Multi-tenant** : conserver `tenant_id` + RLS, ou simplifier ?
6. **Doctrine pédagogique** : mode socratique (ATS) et génération de chapitre
   complet (NURU) coexistent-ils, ou faut-il choisir ?
7. **Exécution de code** : conserve-t-on la sandbox et les tracés générés ?
8. **Échéance** : quelle date cible pour la v1 fusionnée ?

---

## Annexe — Commandes de vérification

```bash
# Volumétrie
find agent-tuteur-api/src -name '*.py' | xargs wc -l | tail -1        # ATS 6 386
find backend -name '*.py' -not -path '*__pycache__*' | xargs wc -l | tail -1  # NURU 7 669

# Tests (exécutés le 2026-07-31)
cd agent-tuteur-api && ../.venv/bin/python -m pytest -q               # 145 passed, 53 skipped
cd nuru-binta && ./venv/bin/python -m pytest tests/ -q                # 84 passed, 1 skipped

# Absence de contrôle d'accès dans NURU
grep -rn "Depends\|Bearer\|token" nuru-binta/backend/app/api/routes/  # 1 seul résultat : un import inutilisé

# Pages frontend NURU sans appel backend
cd nuru-binta/frontend/src && for f in $(find app -name 'page.tsx'); do \
  echo "$(grep -c "from '@/lib/api'" $f)  $f"; done | sort -rn        # 11 lignes à 0

# Hygiène Git
git -C nuru-binta ls-files | wc -l                                    # 1 531
du -sh nuru-binta/.git                                                # 66 Mo
git -C nuru-binta ls-files 'data/processed/chunks/*' | wc -l          # 1 121 pour 102 documents

# Configuration morte
grep -rn "score_threshold" nuru-binta/backend/                        # 1 seul résultat : sa définition
```
