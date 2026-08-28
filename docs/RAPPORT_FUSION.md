# Rapport de fusion — choix adoptés et justifications

> **Mise à jour du 2026-08-27** — le frontend **Next.js** (`agent-tuteur-web-next/`) a été **supprimé du dépôt** : le Vue (`agent-tuteur-web/`) est l'interface unique, celle que le déploiement a toujours servie. Tout ce que ce document dit du Next.js décrit l'état d'alors, pas le dépôt d'aujourd'hui.

**Objet** : rendre compte de la fusion de `rag-agent-pedagogie` (**ATS**) et
`nuru-binta` (**NURU**) en une base unique — ce qui a été décidé, sur quelles
bases, et ce qui reste à trancher.

**Branche** : `feat/fusion` · **Période** : 3–4 août 2026 ·
**Périmètre** : phases P0 à P7 du plan, frontend compris.

Documents liés : [`SYNTHESE_REUNION_TECHNIQUE.md`](SYNTHESE_REUNION_TECHNIQUE.md)
(le plan), [`adr/0010-fusion-nuru-ats.md`](adr/0010-fusion-nuru-ats.md) (la
décision d'architecture), [`../JOURNAL_FUSION.md`](../JOURNAL_FUSION.md) (le
détail, module par module).

---

## 1. En une page

La fusion est **faite**. Les neuf modules du plan sont exécutés, du parsing des
PDF jusqu'au frontend.

| | Avant | Après |
|---|---|---|
| Tests automatisés | 145 | **413** |
| Routes d'API | 17 | **21** |
| Postures de l'agent | 2 (exercice, cours) | **3** (+ quiz) |
| Tables métier | 6 | **11** |
| Fournisseurs de modèle | Mistral, Ollama | **+ Gemini**, ordre configurable |
| Contrôle d'accès aux données d'élève | implicite | **une règle unique, testée** |
| Contrat frontend/API | non typé | **généré depuis OpenAPI** |
| Intégration continue | aucune | **4 vérifications par PR** |

**Le principe suivi** : garder les fondations d'ATS (sécurité, base de données,
architecture) et y greffer le produit de NURU (quiz, suivi de maîtrise, corpus,
parsing PDF). Aucune brique n'a été réécrite pour le plaisir.

**Trois défauts de sécurité ont été corrigés**, dont un que la fusion avait
elle-même introduit.

**Sept points restent à arbitrer** (§7). Le plus important est mesuré : plus de
la moitié du corpus serait aujourd'hui invisible à une recherche filtrée.

---

## 2. Les décisions du plan, et ce qu'elles sont devenues

Les vingt décisions de la synthèse ont toutes été appliquées. Cinq ont demandé
un ajustement en cours de route, justifié par une mesure (§3).

| # | Brique | Décision du plan | Appliquée |
|---|---|---|---|
| D1 | Structure et packaging | ATS | ✅ tel quel |
| D2 | Cœur de l'agent (graphe) | ATS | ✅ tel quel |
| D3 | Posture socratique | ATS | ✅ tel quel |
| D4 | Fusion de scores RAG (RRF) | ATS | ✅ tel quel |
| D5 | Filtrage curriculaire | ATS | ⚠️ appliqué, mais voir **V1** |
| D6 | Priorité cours / complément | NURU | ✅ **ajusté** (§3.1) |
| D7 | Parsing PDF | NURU | ✅ porté |
| D8 | Chunking | ATS | ✅ tel quel |
| D9 | Persistance (infrastructure) | ATS | ✅ tel quel |
| D10 | Modèle de données pédagogique | NURU | ✅ porté, 3 tables écartées (§5) |
| D11 | API et sécurité | ATS | ✅ tel quel |
| D12 | Périmètre fonctionnel de l'API | NURU | ✅ porté (hors enseignant/parent) |
| D13 | Rôles | 4 rôles de NURU | ✅ portés |
| D14 | Chaîne LLM | ATS + Gemini | ✅ **et rendue configurable** (§3.4) |
| D15 | Vérification anti-hallucination | NURU, partiellement | ✅ 2 contrôles sur 5 (§5) |
| D16 | Frontend | Next.js de NURU | ✅ **maintenu malgré la mesure** (§3.5) |
| D17 | Tests | les deux suites | ✅ **réécrits** plutôt que recopiés (§3.3) |
| D18 | Configuration et déploiement | ATS | ✅ tel quel |
| D19 | Corpus | NURU, hors Git | ✅ hors Git |
| D20 | Épinglage des dépendances | réflexe NURU | ✅ appliqué |

---

## 3. Les cinq points où l'exécution a précisé le plan

Chacun repose sur une mesure, pas sur une préférence.

### 3.1 Classer cours et complément demande **deux** signaux, pas un

Le document d'architecture cible (§3a) proposait de se fier au seul découpage
structurel : un morceau intitulé « Chapitre… » est du cours, un morceau
« Exercice… » ne l'est pas.

**Testé sur le corpus réel, cela ne marche pas.** Un TD sans titres explicites
est découpé par une heuristique qui produit des « sous-notions », lesquelles
passent alors pour du cours.

| Règle de classement | Morceaux de TD pris pour du cours |
|---|---|
| Découpage structurel seul | **1 922 sur 2 564 (74 %)** |
| Découpage **+** nature du fichier source | **0** |

La nature du fichier (`data/raw/exercices/…`) tranche donc en dernier ressort.
Un document de TD ne fournit jamais de cours principal, même quand il commence
par des « rappels de cours ».

### 3.2 Aucune classe ni série n'est inventée

NURU remplissait `classe = "Terminale"` et `serie = "S1"` quand l'information
manquait. C'était sans danger chez eux — tout leur corpus est du Terminale S1 —
mais ces deux champs servent à **filtrer ce qu'un élève voit**. Un document
faussement étiqueté apparaîtrait dans les réponses faites à un élève de Seconde.

Un champ vide est préférable à un champ faux. Cet écart a une conséquence
directe, mesurée, qui devient le point **V1** (§7).

### 3.3 Les tests de NURU ont été réécrits, pas recopiés

Le plan prévoyait de reprendre 58 tests « directement réutilisables ». À la
lecture, la plupart ne peuvent pas échouer :

```python
# NURU — l'assertion ne s'exécute que si la condition est déjà vraie
if "serie" in metadata:
    self.assertEqual(metadata["serie"], attendu)

# NURU — l'échec est avalé
except Exception as e:
    pass
```

Vérifié : leur test « scénario réel » **échouerait** s'il ne masquait pas
l'erreur. Leur *intention* — les cas réels du corpus sénégalais — a été portée
avec des assertions qui, elles, échouent quand le comportement change.

### 3.4 L'arbitrage Gemini / Mistral n'a pas eu à être tranché

La question Q2 du plan (quel modèle principal ?) n'avait pas de réponse
évidente : coût, latence depuis le Sénégal, disponibilité, résidence des données
d'élèves mineurs. Elle est devenue un réglage :

```bash
LLM_CHAIN=gemini,mistral,mock   # dans .env — aucune modification de code
```

Vérifié sur cinq configurations réelles. Le dernier maillon reste toujours le
simulacre : **la génération n'échoue jamais complètement**. C'est la différence
avec NURU, où l'absence de clé renvoyait à l'élève un mode d'emploi de
configuration d'API au lieu d'une réponse.

### 3.5 Frontend : la mesure contredisait la recommandation, le choix a été maintenu

Le plan recommandait Next.js parce que NURU avait « 21 écrans déjà conçus »
contre 7 côté Vue. L'état réel a été mesuré avant de reposer la question :

| Mesure | Résultat |
|---|---|
| Endpoints appelés par le frontend NURU | 14 |
| Qui existent dans notre API | **2** (et avec des chemins différents) |
| Qui visent des fonctionnalités reportées (enseignant/parent) ou retirées | 5 |
| Streaming SSE dans le frontend NURU | **aucun** |
| JWT, garde de route et streaming dans le frontend Vue | **les trois, fonctionnels** |

Autrement dit, la plupart des écrans de NURU visent un backend qui n'existe
plus. **L'équipe a maintenu le choix de Next.js après avoir vu ces chiffres** ;
il a donc été appliqué. La mesure est consignée pour mémoire, et explique
pourquoi certains écrans de NURU n'ont pas été repris.

---

## 4. Ce que la fusion a corrigé

### 4.1 Trois défauts de sécurité

| Défaut | Origine | État |
|---|---|---|
| 31 routes d'API sans aucun contrôle d'accès | NURU | **Corrigé** — JWT partout, test 401 sur chaque route |
| La bonne réponse d'un quiz envoyée au navigateur | NURU | **Corrigé** — jeton signé, illisible par le client |
| Un parent pouvait consulter n'importe quel élève | **la fusion elle-même** | **Corrigé** — règle d'accès unique, tests 403 |

Le troisième mérite d'être exposé franchement : en étendant `users.role` à
quatre valeurs (module 3), un contrôle existant est devenu permissif. Il disait
« si ce n'est pas un élève, laisse passer » — juste tant qu'il n'existait que
`admin` et `student`, faux dès l'ajout de `teacher` et `parent`. La règle est
désormais écrite **une seule fois** (`ensure_can_access_student`) et couverte
par des tests par rôle.

### 4.2 Deux défauts fonctionnels silencieux

- **`zip()` sans garde à l'indexation** : si le calculateur d'embeddings
  renvoyait moins de vecteurs que de morceaux, les derniers n'étaient **jamais
  indexés**, sans erreur ni journal. Panne invisible jusqu'à ce qu'un élève ne
  trouve rien.
- **La garde de route du frontend interceptait `/health`** et le redirigeait
  vers le login : le tableau de bord d'administration s'affichait en erreur.

**Aucun des cinq n'aurait été trouvé par les tests unitaires seuls.** Tous
viennent d'une vérification contre l'infrastructure réelle : les 103 PDF, une
vraie base PostgreSQL, un vrai serveur.

---

## 5. Ce qui a été abandonné, et pourquoi

| Élément | Origine | Raison |
|---|---|---|
| Tables `students`, `interactions`, `teachers` | NURU | Doublons de `student_id`, `messages` et `users.role`. `teachers` imposait surtout **deux chemins d'authentification** à sécuriser au lieu d'un |
| `_check_coherence` et `_check_hallucinations` | NURU | Notaient la « cohérence » en comptant les mots « donc », « ainsi ». Un texte **faux** truffé de connecteurs obtenait une bonne note. Une mesure qui ne mesure pas ce qu'elle annonce est pire que pas de mesure |
| `NougatAdapter` | NURU | L'implémentation n'appelle pas l'interface réelle de la bibliothèque ; `nougat` n'étant installé nulle part, le code retombait **toujours** sur PyMuPDF sans que personne ne s'en aperçoive |
| SDK `google-generativeai` | NURU | **Synchrone** : chaque génération bloquerait le serveur entier, pour toutes les requêtes en cours. Remplacé par un appel HTTP asynchrone |
| Repli de connexion d'`AuthContext` | NURU | Déduisait le rôle de l'adresse e-mail quand le backend ne répondait pas : couper son réseau et se connecter avec `admin@…` ouvrait l'administration |
| Replis de données fabriquées | NURU | Des statistiques plausibles masquaient les pannes ; trois chiffres différents circulaient pour la même métrique |
| `create_all()`, repli SQLite | NURU | Ne fait jamais évoluer une table existante — perte de données garantie en production |
| Rerangement TF-IDF par requête | NURU | Réapprenait un modèle sur ~40 documents à chaque question ; remplacé par le RRF |
| Sandbox d'exécution Python | NURU | Aucun tracé ni exécution de code au périmètre : surface d'attaque sans contrepartie. **Décision réversible** |
| `pypdf` comme lecteur principal | ATS | Aplatit les formules mathématiques. Conservé en **repli** |

À retenir : **rien n'a été écarté pour des raisons de style**. Chaque abandon
répond à un défaut vérifiable ou à un doublon.

---

## 6. Ce que la fusion apporte, en chiffres

### Vérifications faites sur l'infrastructure réelle

| Quoi | Résultat |
|---|---|
| PDF du corpus lus sans erreur | **103 / 103** |
| Morceaux produits par le pipeline complet | 6 007 |
| Classement cours / complément | **0 faux positif** sur 2 564 morceaux de TD |
| Migrations, aller **et** retour, sur PostgreSQL 16 | ✅ 13 tables, RLS forcée sur les 5 nouvelles |
| Boucle quiz de bout en bout via le frontend | ✅ correction, maîtrise, 3 badges |
| Streaming SSE via le frontend | ✅ 48 fragments |
| Renommer un champ d'API casse la compilation du frontend | ✅ 6 erreurs, lignes exactes |

### Garanties mises en place

L'intégration continue exécute **quatre vérifications** sur chaque proposition
de modification :

1. analyse statique du code ;
2. **413 tests contre un vrai PostgreSQL** — sans base, 96 tests sont ignorés,
   dont *tous* ceux du contrôle d'accès ;
3. le schéma OpenAPI est régénéré et comparé — il échoue s'il a dérivé du code ;
4. les types du frontend sont régénérés et comparés — ils échouent s'ils ont
   dérivé du schéma.

Les deux derniers sont le mécanisme anti-divergence : **c'est ce qui empêchera
les deux moitiés du projet de se séparer à nouveau.**

---

## 7. Les sept points à trancher en réunion

Le code n'a été modifié dans aucun sens sur ces points : ils attendent une
décision collective. Le détail et les options sont dans
[`JOURNAL_FUSION.md`](../JOURNAL_FUSION.md), section « ⚠️ Points à valider ».

| # | Question | Enjeu |
|---|---|---|
| **V1** | **Plus de la moitié du corpus est invisible à une recherche filtrée par série** | 🔴 **majeur** |
| V4 | Le jeu d'évaluation de recherche n'existe pas → les gains RAG ne sont pas mesurés | 🟠 moyen |
| V7 | Basculer le déploiement vers le nouveau frontend | 🟠 moyen |
| V2 | Faut-il porter `NougatAdapter` ? | 🟢 faible |
| V3 | Que faire de la ligne « Compétences » des documents ? | 🟢 faible |
| V5 | Une bonne explication de quiz peut être écartée par une règle trop stricte | 🟢 faible |
| V6 | Faut-il persister les quiz en base pour analyser la qualité des questions ? | 🟢 faible |

### V1 — le point à traiter en priorité

**Mesuré sur les 103 PDF** :

| Série reconnue | Documents |
|---|---|
| `S1` (exploitable) | 41 |
| aucune | 30 |
| `S` (ambigu) | 25 |
| `TS` (ambigu) | 4 |
| `S2` | 2 |
| `C` (ambigu) | 1 |

Or le filtre exclut un document dont la série ne correspond pas exactement — et
il exclut aussi ceux dont la série est **vide**. Vérifié en exécutant le filtre :

```
chunk sans série  -> retenu ? False
chunk série 'S'   -> retenu ? False
chunk série 'S1'  -> retenu ? True
```

**59 documents sur 103 disparaîtraient** d'une recherche filtrée sur « S1 ».

**D'où viennent les `S` ?** De documents portant « Classe : Terminale S » — la
notation **française**. En regardant les auteurs (`G. COSTANTINI`,
`Jérôme ONILLON`), une partie du dossier `cours/` est constituée de polycopiés
français, pas du programme sénégalais.

Deux questions distinctes, donc :

1. **technique** — une série absente ou ambiguë doit-elle exclure un document ?
   *(avis : non ; un document trouvable mais un peu hors-sujet vaut mieux qu'un
   document introuvable)* ;
2. **contenu** — les polycopiés français ont-ils leur place dans un tuteur du
   programme sénégalais ? Cela rejoint la question Q3 sur les droits d'usage.

### V4 — la mesure qui manque à tous les arbitrages RAG

Le jeu d'évaluation de recherche (30 à 50 questions d'élèves réelles avec le
chapitre attendu) **n'a pas pu être construit** : il demande de vraies questions,
qu'on ne peut pas inventer sans fausser la mesure.

Conséquence directe : le classement cours/complément est **prouvé juste** (0
faux positif sur 2 564 morceaux), mais le fait que remonter le cours en tête
**améliore les réponses** reste une hypothèse raisonnable, pas un résultat.

Le plan le disait déjà : *« sans cette mesure, tous les arbitrages RAG resteront
des opinions invérifiables. »* C'est le point qui demande une contribution
humaine — un enseignant, ou les questions réellement posées par des élèves.

---

## 8. Ce qui reste à faire

| Quoi | Qui | Remarque |
|---|---|---|
| Trancher les sept points du §7 | l'équipe | V1 en priorité |
| Constituer le jeu d'évaluation de recherche | un enseignant | Débloque tous les arbitrages RAG |
| Ingérer les 103 PDF vers Qdrant | dév. données | Le pipeline est prêt et vérifié ; il faut le serveur et le modèle d'embeddings |
| Basculer le déploiement vers le frontend Next.js | dév. + décision | 5 fichiers ; Next exige un processus Node là où le Vue était statique |
| Écrans enseignant et parent | v1.1 | Le modèle de données est déjà posé — c'était le but |
| Archiver `nuru-binta` en lecture seule | **propriétaire du dépôt** | N'a pas été fait depuis ce dépôt |

---

## 9. Ce qu'il faut retenir de la méthode

Trois habitudes ont produit l'essentiel de la valeur, et méritent d'être
conservées après la fusion :

1. **Un module à la fois**, jamais de fusion en bloc. Chaque module se termine
   par une suite de tests verte et une entrée de journal.
2. **Vérifier contre l'infrastructure réelle**, pas seulement par des tests
   unitaires. Les cinq défauts trouvés viennent tous de là : les 103 PDF, une
   vraie base, un vrai serveur.
3. **Ne rien trancher seul** sur un point non prévu. Sept questions sont
   remontées avec leurs options et un avis argumenté, plutôt que décidées en
   silence.

Le nombre de tests n'a jamais diminué : **145 → 413**.
