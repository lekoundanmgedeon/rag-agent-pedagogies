# Synthèse — Réunion technique de convergence

> **📁 Archive — décisions proposées, tranchées depuis.**
>
> Ce document présentait les 20 décisions à prendre et les 8 points à trancher
> collectivement **avant** la fusion. La fusion **a eu lieu** (fusionnée dans
> `main` le 2026-08-06) : les décisions ont été prises et exécutées. Conservé
> pour la trace de ce qui avait été proposé — **plus mis à jour**.
>
> - Ce qui a été décidé et fait : [`RAPPORT_FUSION.md`](RAPPORT_FUSION.md) et
>   [`../JOURNAL_FUSION.md`](../JOURNAL_FUSION.md).
> - Ce qui **reste** à trancher : les sept points **V1 à V7** dans
>   [`STATUS.md`](STATUS.md) §5. Ce ne sont pas les mêmes questions : ils sont
>   apparus *pendant* l'exécution, pas avant.
> - L'arbitrage Gemini/Mistral (question Q2) a été résolu autrement que par un
>   choix : l'ordre de la chaîne est devenu le réglage `.env` `LLM_CHAIN`.

**Objet** : fusionner `rag-agent-pedagogie` (**ATS**) et `nuru-binta` (**NURU**)
en une base unique.
**Date d'analyse** : 2026-07-31 · **Document détaillé** :
[`COMPARATIF_ARCHITECTURES.md`](COMPARATIF_ARCHITECTURES.md)

---

## 1. En une phrase

Les deux équipes ont convergé sur la **même pile** (Python 3.11 · FastAPI ·
LangGraph · Qdrant · BGE-M3 · PostgreSQL · SymPy · KaTeX) ; **ATS a construit
l'infrastructure, NURU a construit le produit et rassemblé les données.** La
fusion consiste donc à **greffer le métier et le corpus de NURU sur la structure
d'ATS**, pas à choisir un gagnant.

---

## 2. Ce que chaque dépôt apporte

| ATS apporte | NURU apporte |
|---|---|
| Architecture hexagonale, cœur testable hors-ligne | **106 PDF du programme réel** (cours, TD, annales, bacs blancs) |
| Graphe LangGraph **async** + streaming SSE | Priorisation **cours vs TD** dans la recherche |
| **Authentification JWT + rôles + RLS** appliquée partout | Chaîne de parsing PDF mathématique (PyMuPDF + Nougat + métadonnées) |
| Migrations **Alembic** + multi-tenant | Modèle **mastery learning** (maîtrise, badges, XP, recommandations) |
| Indices socratiques 0→4, frustration, garde-fous anti-injection | **Quiz + évaluation + correction** (absents d'ATS) |
| Chaîne LLM avec repli (Mistral → Ollama → Mock) | Rôles **enseignant** et **parent** |
| Ingestion asynchrone ARQ + repli gracieux | **21 écrans** frontend, TypeScript + Tailwind 4 |
| Observabilité JSON + trace par nœud | Sandbox d'exécution Python sécurisée |
| **145 tests** sur 3 couches, 9 ADR | **84 tests** unitaires (parsing, métadonnées, quiz) |

---

## 3. Décisions proposées

| # | Brique | Base retenue | Justification en une ligne |
|---|---|---|---|
| D1 | Structure du dépôt & packaging | **ATS** | `pyproject` + layout `src/` + extras ; NURU exige un `sys.path.insert` et un cwd précis |
| D2 | Cœur agent (graphe) | **ATS** | Async + streaming SSE + ports injectables par requête ; NURU est synchrone et bloque la boucle FastAPI |
| D3 | Posture socratique (indices 0→4) | **ATS** | Escalade sur frustration/répétitions, 48 tests ; NURU escalade sur un simple compteur |
| D4 | Fusion de scores RAG | **ATS (RRF)** | Combine des **rangs**, pas des scores d'échelles hétérogènes ; NURU refait un `fit` TF-IDF sur ~40 documents à chaque requête |
| D5 | Filtrage curriculaire | **ATS** | 6 champs + alias de série + clés normalisées (un filtre exact coupait 92 % du corpus) ; NURU filtre sur 2 champs |
| D6 | Priorisation cours/complément | **NURU → à importer** | Sur un corpus majoritairement TD, la recherche sémantique pure remonte des exercices quand l'élève demande un cours |
| D7 | Parsing PDF | **NURU → à importer** | `pypdf` (ATS) détruit les formules ; PyMuPDF + Nougat sont faits pour ça |
| D8 | Chunking | **ATS** | Exercice **indivisible** ; le découpage par taille de NURU sépare un énoncé de son corrigé |
| D9 | Persistance (infrastructure) | **ATS** | Alembic vs `create_all()` : ce dernier ne fait **jamais** évoluer une table existante → perte de données garantie en production |
| D10 | Modèle de données pédagogique | **NURU → à porter** | `ConceptMastery`, `ExerciseResult`, `Badge`, `Recommendation` : ATS n'a rien d'équivalent |
| D11 | API & sécurité | **ATS**, non négociable | NURU expose **31 routes sans aucun contrôle d'accès** (voir §4) |
| D12 | Périmètre fonctionnel de l'API | **NURU → à porter** | Quiz, évaluation, tableau de bord, suivis enseignant/parent |
| D13 | Rôles | **4 rôles de NURU**, portés dans le JWT d'ATS | Périmètre produit plus large, mécanisme d'ATS |
| D14 | Chaîne LLM | **ATS**, + Gemini ajouté comme fournisseur | Sans repli, NURU renvoie à l'élève un mode d'emploi de clé API au lieu d'une réponse |
| D15 | Vérification anti-hallucination | **NURU partiellement** | Garder les 2 contrôles **déterministes** ; écarter les heuristiques « présence de *donc* » |
| D16 | Frontend | **Next.js/TS de NURU**, couche données réécrite | 21 écrans conçus vs 7 ; typage indispensable sur 30+ endpoints. ⚠️ voir Q1 |
| D17 | Tests | **Les deux suites conservées** | 58 tests unitaires de NURU réutilisables tels quels + 45 tests d'API d'ATS |
| D18 | Configuration & déploiement | **ATS** | `pydantic-settings` typée, compose dev **et** prod, nginx, migrations, blueprint Render |
| D19 | Corpus | **NURU**, sorti de Git | Actif irremplaçable, mais 106 PDF n'ont pas leur place dans l'historique Git |
| D20 | Épinglage des dépendances | **Réflexe NURU appliqué à ATS** | NURU documente ses épinglages critiques ; ATS n'a que des bornes `>=` |

---

## 4. Point bloquant à signaler explicitement

> **Le backend NURU n'applique aucun contrôle d'accès.** Le code
> d'authentification existe (`auth_service.py`, PBKDF2 260 k itérations,
> correctement écrit) mais **n'est branché sur aucune route** : `grep` sur
> `backend/app/api/routes/` ne trouve aucun `Depends()` d'authentification,
> aucun jeton, aucun en-tête `Authorization`.

Conséquences vérifiées, sur des données de mineurs :

- `GET /admin/users` → annuaire complet des comptes (emails, rôles) sans authentification ;
- `POST /auth/link-student` prend `user_id` **dans le corps** → n'importe qui peut
  se déclarer parent ou enseignant de n'importe quel élève ;
- `GET /parent/students/{id}` et `GET /teacher/students/{id}` → progression
  nominative de tout élève dont l'identifiant est deviné.

**Côté frontend NURU**, `AuthContext.tsx` aggrave le problème : l'état
d'authentification est un simple objet `localStorage` sans jeton, et le bloc de
repli en cas de backend injoignable déduit le rôle de la chaîne de l'email —

```ts
if (email.includes('admin')) fallbackRole = 'admin';
```

Couper le réseau et se connecter avec `admin@quelquechose.fr` ouvre l'interface
d'administration.

**Ce n'est pas un argument dans le débat d'architecture** : c'est un défaut à
corriger quelle que soit la base retenue. Il explique aussi pourquoi il n'a pas
été détecté : la suite NURU n'a **aucun test de route HTTP**. La règle « un test
négatif 401/403 par route » (phase P4) est le garde-fou à instaurer.

---

## 5. Points à trancher en réunion

### Q1 — Frontend cible : Next.js/TypeScript ou Vue 3 ? ⚠️ *décision structurante*

| | Next.js/TS (recommandé) | Vue 3 conservé |
|---|---|---|
| Écrans déjà conçus | 21 | 7 |
| Typage du contrat d'API | oui (généré depuis OpenAPI) | non (JS pur) |
| Travail restant | recâbler 11 écrans + porter JWT/garde/SSE | concevoir et coder ~14 écrans |
| Risque | compétences React dans l'équipe | dette de typage sur 30+ endpoints |
| Estimation | 10–15 j | 12–18 j |

**Recommandation** : Next.js/TS. Le poste de travail le plus lourd est l'interface,
et NURU l'a déjà fait à moitié ; le typage est le mécanisme de coordination le
moins coûteux entre deux développeurs qui viennent de diverger.
**Condition** : porter impérativement le JWT, la garde de route et le streaming
SSE d'ATS — sans quoi la migration est une régression fonctionnelle.

### Q2 — LLM principal : Gemini ou Mistral ?

À arbitrer sur : coût par million de tokens, latence depuis le Sénégal,
disponibilité de l'API, résidence des données (élèves mineurs), qualité en
français mathématique.
**Recommandation** : ne pas trancher définitivement — conserver le `FallbackRouter`
d'ATS, y ajouter `GeminiLLM`, et rendre l'**ordre configurable**. La décision
devient un réglage `.env`, réversible sans modification de code. Supprimer au
passage le modèle codé en dur (`gemini-3.1-pro-preview` dans `generate.py`).

### Q3 — Corpus : droits et stockage

Les 106 PDF (cours d'enseignants nommés, sujets d'examen, fascicules) sont
actuellement dans l'historique Git.
À trancher : **droits d'usage et de rediffusion** ; stockage cible
(Git LFS vs MinIO/S3) ; qui est responsable de la ré-ingestion et de la mise à
jour du corpus.
**Recommandation** : stockage objet + script d'ingestion versionné ; le dépôt Git
ne contient que le pipeline et un jeu de fixtures.

### Q4 — Périmètre v1 : enseignant et parent inclus ?

Les inclure double le nombre d'écrans et de règles d'accès à tester (un parent ne
doit voir **que** ses enfants — règle à vérifier côté serveur, jamais depuis un
identifiant fourni par le client).
**Recommandation** : v1 = élève + admin (parité avec ATS) ; enseignant et parent
en v1.1, mais **le modèle de données et les rôles sont posés dès la v1** pour
éviter une migration coûteuse.

### Q5 — Multi-tenant : conserver `tenant_id` + RLS ?

C'est un acquis d'ATS qui coûte peu à conserver et très cher à rajouter après.
**Recommandation** : conserver. Décision à confirmer selon le modèle de
déploiement visé (une instance par établissement, ou une instance mutualisée).

### Q6 — Doctrine pédagogique : socratique et cours complet coexistent-ils ?

Les deux dépôts ont deux produits différents :
- **ATS** : posture socratique (indices gradués, l'agent *retient* le contenu) +
  mode cours **navigable section par section** ;
- **NURU** : génération d'un **chapitre de manuel complet** en un seul bloc
  (`/generate/content`), plus proche d'un générateur de support de cours.

Ce n'est pas la même promesse pour l'élève, ni la même pour un enseignant.
**Recommandation** : conserver les deux, mais les **nommer et les séparer**
explicitement dans l'interface — « Je révise avec le tuteur » (socratique) vs
« Je génère une fiche de cours » (enseignant/admin). Ne pas les laisser se
confondre dans un chat unique.

### Q7 — Exécution de code : conserve-t-on la sandbox ?

`sandbox.py` (processus séparé, whitelist de builtins, timeout 5 s) n'est utile
que si l'on conserve la génération de tracés matplotlib ou l'exécution de calculs
produits par le LLM.
**Recommandation** : conserver la sandbox **si et seulement si** les tracés sont
au périmètre ; sinon la retirer — c'est une surface d'attaque sans contrepartie.

### Q8 — Échéance et découpage

Estimation totale : **26 à 41 jours-homme** hors frontend, ou **36 à 56** avec.
Chemin critique : P0 → P1 → P2 → P4 → P5. P3 (domaine pédagogique) est
parallélisable dès P0.
**À trancher** : date de la v1, et répartition (proposition : un développeur sur
données/RAG (P1-P2), l'autre sur domaine/API (P3-P4), les deux sur le frontend).

---

## 6. Actions immédiates si les décisions sont validées

| Quand | Action | Qui |
|---|---|---|
| J+0 | Geler les développements fonctionnels dans les deux dépôts | Les deux |
| J+0 | Créer `feat/fusion` sur ATS | — |
| J+1 | Sortir corpus / `cloudflared` / chunks redondants de l'historique Git NURU | Propriétaire NURU |
| J+1 | Committer `DOCUMENTATION_TECHNIQUE.md` (93 Ko, actuellement non suivi — risque de perte) | Propriétaire NURU |
| J+2 | Mettre en place la CI (`pytest` + `ruff` + `npm run build`) sur `feat/fusion` | — |
| J+2 | Démarrer P1 : parsing PDF + ingestion des 106 PDF + **jeu d'évaluation de recherche** | Dév. données |
| J+2 | Démarrer P3 : migration Alembic du modèle pédagogique | Dév. domaine |
| J+5 | Rédiger l'ADR `0010-fusion-nuru-ats.md` (trace de la décision) | — |

> **Le point le plus important du plan** est le **jeu d'évaluation de recherche**
> (30–50 questions réelles avec chapitre attendu, `recall@5` mesuré avant toute
> optimisation). Sans lui, tous les arbitrages RAG ultérieurs — RRF vs TF-IDF,
> bonus de type, taille des chunks — resteront des opinions invérifiables.
