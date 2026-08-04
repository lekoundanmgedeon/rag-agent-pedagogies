# Reprise du travail de fusion — état au 4 août 2026 (backend + consolidation terminés)

Ce document sert à **reprendre le travail sans rien relire d'autre**. Il dit où
en est la fusion, comment relancer l'environnement, et ce qu'il reste à faire.

- Le détail de chaque décision est dans [`JOURNAL_FUSION.md`](JOURNAL_FUSION.md).
- Le plan d'origine est dans [`docs/COMPARATIF_ARCHITECTURES.md`](docs/COMPARATIF_ARCHITECTURES.md) §7.2.

---

## 1. Où en est-on

**Branche** : `feat/fusion` — 12 commits, tout est sauvegardé, rien en attente.
La branche `main` n'a pas bougé.

**Le backend et la consolidation sont terminés** (modules 0 à 7). Il ne reste
que le frontend, volontairement hors périmètre de ces sessions.

```
1ddb6a7  M7  documentations fusionnées, journal complété
6fee1aa  M7  intégration continue + analyse statique
6330277  (commit intermédiaire)
9d49ed5  (résumé final du journal)
4664114  M6  GeminiLLM et chaîne de repli configurable
a946e46  M5  routes quiz, évaluation et maîtrise
4a19f94  (document de reprise)
b9cb9a8  M5  règle d'accès centralisée + tests 401/403
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
| M5 | Routes API (P4) | ✅ terminé |
| M6 | Gemini + chaîne LLM configurable (P6) | ✅ terminé |
| M7 | Consolidation : ADR, épinglages, ruff, CI (P7) | ✅ terminé |
| — | Frontend (P5) | ⬜ **seul poste restant** |

### Nombre de tests

| Étape | Sans base de données | Avec PostgreSQL |
|---|---|---|
| Départ | 145 | — |
| Après M1 | 177 | — |
| Après M2 | 195 | — |
| Après M3 | 235 | 286 |
| Après M4 | 290 | 341 |
| Après M5 | 290 | 386 |
| **Actuel (M7)** | **317** | **413** |

> Le total « sans base » ne bouge pas au module 5 : les tests ajoutés sont des
> tests d'API, qui exigent PostgreSQL et sont donc ignorés sans lui.

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

# Rapide, sans infrastructure (317 tests)
../.venv/bin/python -m pytest -q

# Complet, avec PostgreSQL (413 tests)
TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost:55432/fusion" \
  ../.venv/bin/python -m pytest -q

# Analyse statique (ce que vérifie aussi l'intégration continue)
../.venv/bin/ruff check .
```

### Dépendance ajoutée

PyMuPDF a été installé dans `.venv` et déclaré dans `pyproject.toml` comme
option `parsing`. Sur une machine neuve :

```bash
pip install -r requirements.txt      # versions exactes validées
pip install -e '.[parsing,dev]'      # PyMuPDF + ruff
```

Sans l'option `parsing`, la lecture des PDF retombe sur `pypdf` et **abîme les
formules** sans prévenir — seulement une ligne de journal.

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
- **M5** — Les routes `/api/quiz`, `/api/quiz/answer`, `/api/evaluation/{id}` et
  `/api/mastery/{id}`, toutes protégées. La règle « qui a le droit de voir quel
  élève » est écrite une seule fois. **Une faille a été refermée au passage** :
  les rôles ajoutés au M3 laissaient un parent consulter n'importe quel élève.
  Et la bonne réponse d'un quiz ne descend plus dans le navigateur.
- **M6** — Gemini ajouté comme fournisseur, et l'ordre de la chaîne de repli
  devient un réglage `.env` (`LLM_CHAIN`). Changer de modèle ne demande plus
  aucune modification de code.
- **M7** — ADR 0010, dépendances épinglées, analyse statique configurée, et
  **intégration continue** : quatre vérifications sur chaque proposition de
  modification (ruff, tests avec PostgreSQL, schéma OpenAPI, build frontend).
  Un défaut réel trouvé au passage : `zip()` sans garde à l'indexation laissait
  des morceaux non indexés en silence.

---

## 4. Ce qu'il reste à faire

### 4.1 P5 — Frontend *(seul poste restant)*

Le poste le plus long du plan (10 à 15 jours). Le contrat est prêt : le schéma
OpenAPI se génère par `python scripts/export_openapi.py`, et les types
TypeScript s'en déduisent (`npx openapi-typescript`). Voir §7 de
`docs/ARCHITECTURE_CIBLE.md` pour les trois acquis à porter impérativement
(jeton JWT, garde de route, streaming SSE).

### 4.2 Ce qui n'a pas été fait et qui demande une décision humaine

- **Le jeu d'évaluation de recherche** (P1.4) — 30 à 50 vraies questions
  d'élèves avec le chapitre attendu. Sans lui, on ne peut pas prouver que le
  re-ranker du M2 améliore les réponses. Le plan le désigne comme *« le point le
  plus important »*. Il demande une contribution humaine (un enseignant, ou les
  questions réellement posées).
- **L'ingestion des 103 PDF vers Qdrant** (P1.3) — le pipeline fonctionne et a
  été vérifié de bout en bout (6 007 morceaux produits), mais rien n'a été
  indexé : cela suppose un serveur Qdrant et le modèle d'embeddings BGE-M3, tous
  deux absents de cette machine.
- **Le frontend** (P5) — hors périmètre décidé pour ces sessions.
- **L'archivage de `nuru-binta`** en lecture seule, avec un `README` renvoyant
  ici. Cette action appartient à son propriétaire : elle n'a pas été faite
  depuis ce dépôt.

---

## 5. Les décisions en attente de validation

Six points sont remontés dans la section **« ⚠️ Points à valider »** de
`JOURNAL_FUSION.md`. Le code n'a été modifié dans aucun sens : ils attendent un
arbitrage d'équipe.

| # | Sujet | Gravité |
|---|---|---|
| **V1** | **57 % du corpus serait invisible** à une recherche filtrée par série (mesuré : 59 documents sur 103) | 🔴 **le plus important** |
| V2 | Faut-il porter `NougatAdapter` ? (non porté : l'implémentation de NURU ne fonctionne pas) | 🟢 faible |
| V3 | Que faire de la ligne « Compétences » des documents ? | 🟢 faible |
| V4 | Le jeu d'évaluation de recherche n'existe pas → les gains du M2 ne sont pas mesurés | 🟠 moyenne |
| V5 | Une bonne explication de quiz peut être jetée par une règle trop stricte | 🟢 faible |
| V6 | Faut-il persister les quiz en base (pour analyser la qualité des questions) ? | 🟢 faible |

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
git log --oneline -9          # retrouver le fil

# Relancer la base de test (§2), puis vérifier que tout est sain :
cd agent-tuteur-api
TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost:55432/fusion" \
  ../.venv/bin/python -m pytest -q      # doit afficher 413 passed

../.venv/bin/ruff check .               # doit afficher : All checks passed!
```

Si ces 413 tests passent et que l'analyse statique est propre, l'état est sain.
Le seul poste restant est le frontend (§4.1) — il suppose que l'équipe ait
tranché la question Q1 du plan (Next.js ou Vue).
