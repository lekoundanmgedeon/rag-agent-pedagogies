# ADR 0010 — Fusion des dépôts NURU et ATS

## Contexte

Deux équipes ont développé en parallèle, sans coordination, un tuteur
pédagogique pour le programme scolaire sénégalais :

- **ATS** (`rag-agent-pedagogie`, ce dépôt) — architecture hexagonale, graphe
  LangGraph async, streaming SSE, authentification JWT + RLS multi-tenant,
  migrations Alembic, 145 tests, 9 ADR ;
- **NURU** (`nuru-binta`) — 103 PDF du programme réel, quiz et évaluation,
  modèle *mastery learning*, rôles enseignant/parent, 21 écrans frontend,
  parsing PDF mathématique.

Les deux ont convergé sur la **même pile** (Python 3.11, FastAPI, LangGraph,
Qdrant, BGE-M3, PostgreSQL, SymPy, KaTeX). ATS a construit l'infrastructure,
NURU a construit le produit et rassemblé les données. Poursuivre en parallèle
aurait doublé le coût de maintenance sans bénéfice.

L'analyse comparative complète est dans
[`COMPARATIF_ARCHITECTURES.md`](../COMPARATIF_ARCHITECTURES.md) ; la synthèse de
décision dans [`SYNTHESE_REUNION_TECHNIQUE.md`](../SYNTHESE_REUNION_TECHNIQUE.md).

## Décision

**Le dépôt ATS est la base structurelle ; le métier, le corpus et le frontend de
NURU y sont greffés.** Ce n'est pas le choix d'un gagnant : c'est le constat que
l'infrastructure est plus coûteuse à reconstruire que le métier à porter.

La fusion a été exécutée **module par module** sur la branche `feat/fusion`,
chaque module se terminant par une suite de tests verte et une entrée dans
[`JOURNAL_FUSION.md`](../../JOURNAL_FUSION.md).

### Repris d'ATS, sans modification

Cœur hexagonal et ports · graphe LangGraph async + double compilation SSE ·
indices socratiques 0→4, frustration, garde-fous · taxonomie curriculaire et
fusion RRF · chunking structurel (exercice indivisible) · persistance Alembic +
RLS + `tenant_id` · JWT, bcrypt, `Principal`, limitation de débit · ARQ et son
repli · observabilité JSON et trace par nœud.

### Porté de NURU, adapté aux conventions du dépôt

| Apport | Adaptation |
|---|---|
| Parsing PDF (PyMuPDF, `cleaners`, 3 extracteurs de métadonnées) | Travail sur des octets et non des chemins ; fonctions plutôt que classes ; alignement sur la taxonomie |
| Priorisation cours / complément | Re-ranker **au-dessus** du RRF, jamais à sa place |
| Modèle *mastery learning* | UUID, `tenant_id`, `Mapped[]`, RLS, migrations Alembic |
| Quiz, évaluation, correction | `async`, derrière `BaseLLM`, sans fournisseur ni niveau codés en dur |
| Rôles enseignant et parent | Portés dans `users.role` + JWT, avec `student_links` |
| Gemini | Fournisseur `httpx` ajouté à la chaîne de repli existante |
| Tests unitaires (parsing, métadonnées, quiz) | Réécrits avec de vraies assertions (voir Justification) |

### Abandonné

- **`create_all()` et le repli SQLite** — aucune évolution de schéma possible ;
- **`sys.path.insert` et les imports `backend.app.*`** — remplacés par le
  packaging `src/` ;
- **Le reranking TF-IDF réajusté à chaque requête** — superseded par le RRF ;
- **Les tables `students`, `interactions`, `teachers`** — doublons de
  `student_id`, `messages` et `users.role` ;
- **`_check_coherence` et `_check_hallucinations`** — heuristiques sans
  fondement (voir Justification) ;
- **`AuthContext` avec repli local de connexion** — élévation de privilège ;
- **La sandbox d'exécution Python** — surface d'attaque sans contrepartie tant
  que les tracés ne sont pas au périmètre (décision de cadrage).

## Justification

- **ATS comme base plutôt que NURU** : l'authentification, la RLS multi-tenant
  et les migrations sont des acquis coûteux à reconstruire et impossibles à
  rétro-ajouter proprement. À l'inverse, le métier de NURU (quiz, maîtrise) est
  du code sans dépendance d'infrastructure, donc portable. Le point décisif :
  **le backend NURU n'appliquait aucun contrôle d'accès** — le code
  d'authentification existait mais n'était branché sur aucune route.

- **Re-ranker au-dessus du RRF, pas à sa place** : le RRF combine des *rangs*,
  dont l'échelle n'a pas de signification interprétable. Y appliquer un bonus de
  score serait arbitraire. On partitionne donc le classement produit sans
  toucher aux scores.

- **Deux signaux pour classer cours et complément**, alors que
  [`ARCHITECTURE_CIBLE.md`](../ARCHITECTURE_CIBLE.md) §3a n'en prévoyait qu'un.
  Mesuré sur le corpus réel : le seul `type_chunk` classait **1 922 morceaux de
  TD sur 2 564 (74 %)** comme du cours, parce qu'un TD sans titres explicites est
  découpé en « sous-notions ». La nature du fichier source tranche en dernier
  ressort.

- **Moyenne mobile exponentielle pour la maîtrise** (formule de NURU conservée)
  plutôt qu'un simple ratio : deux élèves ayant 5 échecs et 5 réussites ne sont
  pas dans le même état si l'un progresse et l'autre régresse. Le score dépend
  de l'ordre des tentatives, donc n'est pas recalculable depuis les compteurs —
  mais il reste reconstituable en rejouant `exercise_results`.

- **Deux contrôles de vérification sur cinq** : seuls ceux reposant sur un fait
  vérifiable ont été portés (vocabulaire hors-programme, présence du résultat
  calculé). `_check_coherence` notait la cohérence en comptant les mots « donc »
  et « ainsi » : un texte faux truffé de connecteurs obtenait une bonne note.
  Une mesure qui ne mesure pas ce qu'elle annonce est pire que pas de mesure.

- **Tests réécrits plutôt que recopiés** : les tests de NURU étaient
  conditionnels (`if "serie" in metadata: assert…`) ou enveloppés dans un
  `except: pass`. Leurs assertions ne s'exécutaient presque jamais — vérifié :
  leur test « scénario réel » échouerait s'il ne masquait pas l'erreur. Leur
  *intention* a été portée avec des assertions qui échouent réellement.

- **Chaîne LLM configurable plutôt qu'un arbitrage Gemini/Mistral** : la
  question Q2 de la synthèse n'avait pas de réponse évidente (coût, latence
  depuis le Sénégal, résidence des données d'élèves mineurs). `LLM_CHAIN` la
  transforme en réglage réversible.

- **La bonne réponse d'un quiz ne descend pas au client** : NURU renvoyait
  `correct_answer` au navigateur. Elle voyage désormais dans un jeton signé —
  solution sans état, qui n'a demandé aucune table supplémentaire.

## Conséquences

- **Trois défauts de sécurité corrigés**, dont un introduit par la fusion
  elle-même : l'extension de `users.role` à quatre valeurs a rendu permissif un
  contrôle qui disait « si ce n'est pas un élève, laisse passer ». La règle
  d'accès est désormais centralisée dans
  `api/dependencies.ensure_can_access_student` et couverte par des tests 401/403.

- **Les migrations `0006` et `0007` sont à appliquer** (`alembic upgrade head`).
  Les documents déjà indexés doivent être **ré-ingérés** pour recevoir le champ
  `type_document`, sans quoi ils seront tous traités comme des compléments.

- **PyMuPDF est un extra optionnel** (`pip install -e '.[parsing]'`). Sans lui,
  l'ingestion retombe sur `pypdf` et dégrade les formules **sans avertissement
  visible** — seulement une ligne de log.

- **Les rôles `teacher` et `parent` existent en base sans écrans associés**
  (décision de cadrage : v1.1). Un compte portant ces rôles n'a accès à rien
  tant qu'aucune ligne `student_links` ne le rattache à un élève.

- **La suite de tests passe de 145 à 413** (317 hors base de données). Les tests
  d'API exigent PostgreSQL et sont ignorés sans lui — d'où l'intégration
  continue, qui en fournit un.

- **Ce qui n'a pas pu être fait, et qui reste bloquant pour mesurer le RAG** :
  le jeu d'évaluation de recherche (30 à 50 questions d'élèves réelles avec le
  chapitre attendu). Sans lui, le gain du re-ranker pédagogique est une
  hypothèse raisonnable, pas un résultat. Le plan le désigne comme *« le point
  le plus important »*.

- **Six arbitrages restent ouverts**, listés dans la section « ⚠️ Points à
  valider » de [`JOURNAL_FUSION.md`](../../JOURNAL_FUSION.md). Le plus important
  (**V1**) est mesuré : **59 documents sur 103** seraient invisibles à une
  recherche filtrée par série, et une partie du dossier `cours/` s'avère être
  des polycopiés français, pas le programme sénégalais.

- **Le dépôt `nuru-binta` doit être archivé en lecture seule** avec un `README`
  pointant ici. Cette action appartient à son propriétaire — elle n'a pas été
  faite depuis ce dépôt.
