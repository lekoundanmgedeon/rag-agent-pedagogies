# Reprise du travail de fusion — état au 4 août 2026

Ce document sert à **reprendre le travail sans rien relire d'autre**. Il dit où
en est la fusion, comment relancer l'environnement, et ce qu'il reste à faire.

- Le détail de chaque décision est dans [`JOURNAL_FUSION.md`](JOURNAL_FUSION.md).
- Le plan d'origine est dans [`docs/COMPARATIF_ARCHITECTURES.md`](docs/COMPARATIF_ARCHITECTURES.md) §7.2.

---

## 1. Où en est-on

**Branche** : `feat/fusion` — 5 commits, tout est sauvegardé, rien en attente.
La branche `main` n'a pas bougé.

```
b9cb9a8  M5 (en cours) règle d'accès centralisée + tests 401/403
f426c02  M4  branche quiz, vérification déterministe, suivi de maîtrise
1e3f005  M3  modèle de données pédagogique et rôles étendus
2d9532a  M2  re-ranker cours/complément au-dessus du RRF
b28d1a4  M1  parsing PDF PyMuPDF + extracteurs de métadonnées
cab7ecf  (départ, sur main)
```

### Avancement par module

| Module | Sujet | État |
|---|---|---|
| M0 | Branche, journal, mesure de référence | ✅ terminé |
| M1 | Lecture des PDF + métadonnées (phase P1 du plan) | ✅ terminé |
| M2 | Priorité au cours dans la recherche (P2) | ✅ terminé |
| M3 | Modèle de données pédagogique + rôles (P3.1-P3.2) | ✅ terminé |
| M4 | Quiz, vérification, maîtrise (P3.3-P3.5) | ✅ terminé |
| M5 | Routes API (P4) | 🟡 **en cours — voir §4** |
| M6 | Gemini + chaîne LLM configurable (P6) | ⬜ pas commencé |
| — | Frontend (P5) | ⬜ hors périmètre décidé |
| — | Consolidation, ADR, CI (P7) | ⬜ pas commencé |

### Nombre de tests

| Étape | Sans base de données | Avec PostgreSQL |
|---|---|---|
| Départ | 145 | — |
| Après M1 | 177 | — |
| Après M2 | 195 | — |
| Après M3 | 235 | 286 |
| Après M4 | 290 | 341 |
| **Actuel** | **290** | **359** |

> Le total « sans base » n'a pas bougé entre M4 et l'actuel : les 18 tests
> ajoutés sont des tests d'API, qui exigent PostgreSQL et sont donc ignorés
> sans lui.

---

## 2. Remettre l'environnement en marche

### Base PostgreSQL de test

Une base jetable avait été créée pour vérifier les migrations. Si elle n'est
plus là, la recréer :

```bash
docker run -d --name fusion-pg-test \
  -e POSTGRES_PASSWORD=test -e POSTGRES_USER=test -e POSTGRES_DB=fusion \
  -p 55432:5432 postgres:16-alpine

cd agent-tuteur-api
DATABASE_URL="postgresql+asyncpg://test:test@localhost:55432/fusion" \
  ../.venv/bin/alembic upgrade head
```

> ⚠️ Les conteneurs `nuru_postgres`, `nuru_redis` et `erp-db-demo` qui tournent
> sur cette machine **ne nous appartiennent pas** — ne pas les arrêter. Le port
> 55432 a été choisi pour ne rien percuter.

### Lancer les tests

```bash
cd agent-tuteur-api

# Rapide, sans infrastructure (290 tests)
../.venv/bin/python -m pytest -q

# Complet, avec PostgreSQL (359 tests)
TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost:55432/fusion" \
  ../.venv/bin/python -m pytest -q
```

### Dépendance ajoutée

PyMuPDF a été installé dans `.venv` et déclaré dans `pyproject.toml` comme
option `parsing`. Sur une machine neuve :

```bash
pip install -e '.[parsing]'
```

Sans elle, la lecture des PDF retombe sur `pypdf` et **abîme les formules** sans
prévenir.

### Le corpus

Les 103 PDF sont dans `~/nuru/nuru-binta/data/raw/` (dossiers `cours/` et
`exercices/`). Ils ne sont **pas** dans ce dépôt, conformément au plan.

---

## 3. Ce qui a été fait, en bref

*(le détail est dans `JOURNAL_FUSION.md`, une section par module)*

- **M1** — PyMuPDF remplace `pypdf` pour lire les PDF (les formules étaient
  détruites). Trois extracteurs de métadonnées portés de NURU. Vérifié sur les
  103 PDF réels : aucune erreur de lecture.
- **M2** — La recherche remonte maintenant le **cours** en tête quand l'élève
  demande une explication, et l'agent **avoue** quand le corpus n'a que des TD
  au lieu d'inventer un cours.
- **M3** — Cinq tables portées de NURU (maîtrise, résultats, badges,
  recommandations, liaisons). Migrations vérifiées sur PostgreSQL réel, aller
  **et** retour. Trois tables de NURU supprimées car en doublon.
- **M4** — L'agent sait **interroger** l'élève (troisième posture, à côté de
  « exercice » et « cours »), **vérifier** ce qu'il produit, et **enregistrer**
  les réussites.
- **M5 (partiel)** — La règle « qui a le droit de voir quel élève » est écrite
  une seule fois et testée. **Au passage, une faille a été refermée** : les
  rôles ajoutés au M3 laissaient un parent consulter n'importe quel élève.

---

## 4. Ce qu'il reste à faire

### 4.1 Terminer M5 — les routes API *(prochaine étape)*

Ce qui est **fait** : la règle d'accès, les dépendances de repositories, les
tests 401/403.

Ce qui **reste** :

1. **`routes/quiz.py`** — `POST /api/quiz` (générer) et `POST /api/quiz/answer`
   (corriger et enregistrer le résultat). La logique existe déjà dans
   `agent/quiz.py` : il s'agit de l'exposer.
2. **`routes/evaluation.py`** — `GET /api/evaluation/{student_id}` : historique
   des exercices et quiz. Passer par `ensure_can_access_student`.
3. **`routes/mastery.py`** — `GET /api/mastery/{student_id}` : niveau par
   compétence, badges, compétences les plus faibles.
4. **Brancher les ports pédagogiques sur le chat** : `MasteryPort` doit être
   injecté par requête dans `routes/chat.py`, comme le sont déjà `memory` et
   `audit`.
5. **Schémas de réponse** dans `api/schemas.py` (le projet répond toujours par
   des modèles typés, jamais des dictionnaires bruts).
6. **Étendre `test_access_control.py`** aux nouvelles routes — la liste
   paramétrée est déjà en place, il suffit d'y ajouter les chemins.
7. **Régénérer le schéma OpenAPI** (il servira de source aux types du frontend).

> **Décision déjà prise à respecter** : les routes `/api/teacher` et
> `/api/parent` sont **reportées** en v1.1. Le modèle de données est posé, les
> écrans ne le sont pas.

### 4.2 M6 — Gemini et chaîne LLM configurable *(indépendant, peut être fait en premier)*

1. `agent/llm/gemini.py` — sur le modèle de `mistral.py`, en `httpx` et non avec
   le SDK Google (qui est synchrone et bloquerait le serveur).
2. `agent/llm/router.py` — rendre l'ordre de la chaîne configurable par une
   variable `LLM_CHAIN` (ex. `"gemini,mistral,mock"`). Le dernier maillon reste
   toujours le simulacre : la génération ne doit jamais échouer complètement.
3. `config/settings.py` — `gemini_api_key`, `gemini_model`, `llm_chain`.
4. Tests de bascule, sur le modèle des 6 tests existants de `test_llm_fallback.py`.

C'est le module le plus court (1 à 2 jours dans le plan) et il ne dépend de rien.

### 4.3 P7 — Consolidation *(après M5 et M6)*

1. ADR `docs/adr/0010-fusion-nuru-ats.md` — la trace de la décision.
2. Répartir le contenu utile de `DOCUMENTATION_TECHNIQUE.md` de NURU (93 Ko)
   dans `architecture.md` / `api.md` — **pas de recopie en bloc**.
3. Épingler les versions critiques dans `pyproject.toml`.
4. **Mettre en place l'intégration continue** (`pytest` + `ruff` + build du
   frontend). C'est la garantie que les deux dépôts ne re-divergeront pas.

### 4.4 Ce qui n'a pas été fait et qui demande une décision humaine

- **Le jeu d'évaluation de recherche** (P1.4) — 30 à 50 vraies questions
  d'élèves avec le chapitre attendu. Sans lui, on ne peut pas prouver que le
  re-ranker du M2 améliore les réponses. Le plan le désigne comme *« le point le
  plus important »*. Il demande une contribution humaine (un enseignant, ou les
  questions réellement posées).
- **L'ingestion des 103 PDF vers Qdrant** (P1.3) — le pipeline fonctionne et a
  été vérifié de bout en bout (6 007 morceaux produits), mais rien n'a été
  indexé : cela suppose un serveur Qdrant et le modèle d'embeddings BGE-M3, tous
  deux absents de cette machine.
- **Le frontend** (P5) — hors périmètre décidé pour cette session.

---

## 5. Les décisions en attente de validation

Cinq points sont remontés dans la section **« ⚠️ Points à valider »** de
`JOURNAL_FUSION.md`. Le code n'a été modifié dans aucun sens : ils attendent un
arbitrage d'équipe.

| # | Sujet | Gravité |
|---|---|---|
| **V1** | **57 % du corpus serait invisible** à une recherche filtrée par série (mesuré : 59 documents sur 103) | 🔴 **le plus important** |
| V2 | Faut-il porter `NougatAdapter` ? (non porté : l'implémentation de NURU ne fonctionne pas) | 🟢 faible |
| V3 | Que faire de la ligne « Compétences » des documents ? | 🟢 faible |
| V4 | Le jeu d'évaluation de recherche n'existe pas → les gains du M2 ne sont pas mesurés | 🟠 moyenne |
| V5 | Une bonne explication de quiz peut être jetée par une règle trop stricte | 🟢 faible |

**V1 est à traiter en priorité** : il touche la décision D5 du comparatif
(filtrage curriculaire) et conditionne l'utilité réelle du corpus. Il révèle
aussi qu'une partie du dossier `cours/` est constituée de polycopiés **français**
(auteurs `G. COSTANTINI`, `Jérôme ONILLON`) et non du programme sénégalais —
ce qui rejoint la question Q3 du plan sur les droits d'usage du corpus.

---

## 6. Règles de travail à garder en tête

Ce sont celles suivies jusqu'ici ; les abandonner ferait perdre la cohérence de
l'ensemble.

1. **Un module à la fois**, jamais de fusion en bloc.
2. **Après chaque module** : la suite de tests passe, et le nombre de tests ne
   diminue jamais.
3. **Les tests unitaires ne suffisent pas** — chaque module a été vérifié contre
   l'infrastructure réelle (les 103 PDF, PostgreSQL). C'est ainsi que la faille
   d'accès du M5 et l'erreur de classement du M2 ont été trouvées.
4. **Documenter dans `JOURNAL_FUSION.md`** au fur et à mesure, en langage simple :
   ce qui est gardé, retiré, ajouté, et l'impact.
5. **Ne rien trancher seul** sur un point non prévu par le plan : l'ajouter à
   « ⚠️ Points à valider » avec les options et un avis argumenté.
6. **Ne jamais toucher aux conteneurs Docker** qui ne sont pas à nous.

---

## 7. Pour reprendre, concrètement

```bash
cd ~/nuru/rag-agent-pedagogie
git checkout feat/fusion
git log --oneline -6          # retrouver le fil

# Relancer la base de test (§2), puis vérifier que tout est sain :
cd agent-tuteur-api
TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost:55432/fusion" \
  ../.venv/bin/python -m pytest -q      # doit afficher 359 passed
```

Si ces 359 tests passent, l'état est sain et vous pouvez enchaîner sur le §4.1
(terminer M5) ou le §4.2 (M6, indépendant).
