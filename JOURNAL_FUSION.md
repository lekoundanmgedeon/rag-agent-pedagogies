# Journal de fusion — `rag-agent-pedagogie` (ATS) × `nuru-binta` (NURU)

Ce fichier raconte, module par module, **ce qui a été fusionné, pourquoi, et ce
que ça change pour vous**. Il est écrit pour être lisible par quelqu'un qui
découvre le projet : chaque terme technique est expliqué la première fois qu'il
apparaît.

**Branche de travail** : `feat/fusion` · **Base de départ** : ATS (`rag-agent-pedagogie`)

---

## Le contexte en trois phrases

Deux équipes ont construit, chacune de son côté, un tuteur pédagogique pour le
programme scolaire sénégalais. Les deux ont choisi les mêmes outils, mais l'une
(ATS) a surtout bâti les **fondations** (sécurité, base de données, architecture),
l'autre (NURU) a surtout bâti le **produit** (quiz, suivi des élèves, corpus de
103 PDF réels). La fusion consiste donc à **greffer le métier de NURU sur les
fondations d'ATS** — pas à désigner un gagnant.

Le détail des arbitrages est dans [`docs/COMPARATIF_ARCHITECTURES.md`](docs/COMPARATIF_ARCHITECTURES.md)
et [`docs/SYNTHESE_REUNION_TECHNIQUE.md`](docs/SYNTHESE_REUNION_TECHNIQUE.md).

---

## Décisions de cadrage validées avant démarrage

| Question | Décision retenue |
|---|---|
| Rôles enseignant / parent | **Modèle de données posé maintenant**, écrans et routes reportés en v1.1 |
| Sandbox d'exécution de code Python de NURU | **Non portée** — aucun tracé ni exécution de code au périmètre actuel |
| Périmètre de cette session | Backend complet (modules 0 à 6), **frontend exclu** |

---

## Module 0 : Mise en place de la fusion

### Ce qui a été gardé

- **Le dépôt ATS comme base** — c'est lui qui contient les fondations
  (authentification, migrations de base de données, tests). On construit dessus
  plutôt que de repartir de zéro.
- **La suite de tests existante d'ATS** — elle sert de filet de sécurité : si un
  portage casse quelque chose, elle le signale immédiatement.

### Ce qui a été retiré

- Rien à ce stade. Le module 0 ne fait que préparer le terrain.

### Ce qui a été ajouté ou modifié

- **Branche `feat/fusion`** — tout le travail de fusion s'y déroule, ce qui laisse
  la branche `main` intacte et permet de revenir en arrière à tout moment.
- **Ce fichier `JOURNAL_FUSION.md`** — la trace écrite de chaque décision.
- **Mesure de référence** : avant toute modification, la suite de tests a été
  lancée. Résultat de départ : **145 tests passent, 53 sont ignorés**.
  Les tests ignorés sont ceux qui ont besoin de services externes non démarrés
  (la base PostgreSQL, le moteur de recherche Qdrant, le modèle d'embeddings).
  C'est normal en local.

  > **Embeddings** : transformation d'un texte en une liste de nombres, pour que
  > la machine puisse mesurer si deux textes parlent de la même chose.
  > **Qdrant** : la base de données qui stocke ces listes de nombres et retrouve
  > les plus proches d'une question posée.

### Impact sur le reste du projet

Ce chiffre de **145 tests** est le seuil de référence : à la fin de chaque module,
la suite doit toujours passer, et le nombre de tests ne doit jamais diminuer. Si
vous reprenez ce projet, lancez `pytest` depuis `agent-tuteur-api/` avant de
commencer — vous saurez tout de suite si l'état de départ est sain.

---

## Module 1 : Lecture des PDF et reconnaissance des métadonnées

**Objectif** : pouvoir lire correctement les 103 PDF du programme réel, et
deviner automatiquement de quoi parle chaque document (quelle classe, quelle
série, quel chapitre).

### Ce qui a été gardé

- **`pypdf`, l'ancien lecteur de PDF d'ATS** — il n'est plus le lecteur
  principal, mais il reste en **repli**. Si la nouvelle bibliothèque n'est pas
  installée ou échoue sur un fichier, l'ingestion continue au lieu de s'arrêter.
- **L'interface publique `extract_text()` / `load_file()`** — les fonctions que
  le reste du code appelle n'ont pas changé de nom ni de signature. Tout le
  travail est interne : aucun appelant n'a eu à être modifié.
- **Les expressions régulières de NURU** — voir plus bas, c'est l'apport
  principal du module.

  > **Expression régulière** (« regex ») : une façon de décrire une forme de
  > texte à rechercher, par exemple « le mot *Chapitre* suivi d'un numéro ».

### Ce qui a été retiré

- **`pypdf` comme lecteur principal** — il abîme les mathématiques : les
  fractions, indices et exposants sont aplatis, et l'ordre de lecture des
  colonnes est souvent faux. Mesuré sur le corpus : sur `07_Suites_numeriques.pdf`,
  PyMuPDF restitue `u : I ⊂ N → R` et `f′ ≥ 0`, là où `pypdf` perdait les
  symboles.
- **La classe `MetadataConfig` de NURU** — c'était un objet à instancier pour
  transporter des motifs qui ne changent jamais. Les motifs sont maintenant de
  simples constantes de fichier : moins de code, même résultat.
- **Les valeurs par défaut inventées** (`classe = "Terminale"`, `serie = "S1"`)
  — NURU remplissait ces champs quand l'information manquait. C'était sans
  danger chez eux (tout leur corpus est du Terminale S1), mais **dangereux
  ici** : ces deux champs servent à filtrer ce qu'un élève voit. Un document
  faussement étiqueté « Terminale S1 » apparaîtrait dans les réponses faites à
  un élève de Seconde. On préfère un champ vide à une valeur fausse.
- **Les champs `pays`, `langue` et `document_id`** — les deux premiers valent
  toujours la même chose dans tout le projet, le troisième faisait doublon avec
  l'identifiant de document déjà géré en base de données.
- **`NougatAdapter`** — non porté, voir les points à valider ci-dessous.

### Ce qui a été ajouté ou modifié

Le fichier `ingestion/loaders.py` est devenu un **dossier** `ingestion/loaders/`,
pour accueillir les nouvelles briques sans faire grossir un seul fichier :

| Fichier | Ce qu'il fait |
|---|---|
| `loaders/__init__.py` | Le point d'entrée, inchangé pour les appelants |
| `loaders/pdf.py` | Lecture d'un PDF : PyMuPDF d'abord, `pypdf` en repli |
| `loaders/cleaners.py` | Nettoyage : retire les en-têtes répétés, uniformise les formules |
| `loaders/metadata/patterns.py` | Les motifs de reconnaissance (série, chapitre, année…) |
| `loaders/metadata/from_filename.py` | Ce que dit le **nom** du fichier et son dossier |
| `loaders/metadata/from_content.py` | Ce que dit l'**en-tête** du document |
| `loaders/metadata/merge.py` | Fusionne les deux et aligne sur la taxonomie du projet |

Deux autres changements :

- **`config/taxonomy.py`** : `TS1` et `TS2` sont désormais reconnus comme des
  **alias** de `S1` et `S2`. « TS1 » veut dire « Terminale S1 » : c'est la forme
  employée dans les noms de fichiers et par les élèves eux-mêmes. Sans cet
  alias, un élève écrivant « TS1 » ne trouvait aucun document annoté « S1 ».
  Attention à ne pas confondre avec `T1`/`T2`, qui sont les séries *techniques*.
- **`pyproject.toml`** : nouvelle option d'installation `parsing`
  (`pip install '.[parsing]'`) qui apporte PyMuPDF. Elle est **facultative** :
  le projet fonctionne sans, en mode repli.

### Vérification faite sur les données réelles

Les tests unitaires ne suffisent pas à prouver qu'un lecteur de PDF fonctionne.
Les 103 PDF du corpus ont donc été passés en revue :

| Ce qui a été mesuré | Résultat |
|---|---|
| PDF lus sans erreur | **103 / 103** |
| Chapitre identifié automatiquement | 43 / 103 (41 %) |
| Lignes supprimées par le nettoyage | 676, **toutes** de vrais en-têtes (`« Page 3 »`, `« Lycée de Dioudé Diabé »`, `« Prof : M.Djitté »`) — aucun contenu mathématique perdu |

Le nettoyage retire jusqu'à 40 % d'un document court : c'est normal, ces
fichiers répètent l'en-tête de l'établissement à chaque page.

### Tests

**+32 tests** (145 → **177**, tous au vert).

Les tests de NURU ont été portés dans leur *intention*, pas à la lettre : les
originaux étaient écrits sous conditions
(`if "serie" in metadata: assert…`) ou enveloppés dans un `except: pass`, si
bien que leurs assertions ne s'exécutaient presque jamais. La vérification l'a
confirmé : leur test « scénario réel » échouerait s'il n'avalait pas l'erreur.
Les nouveaux tests, eux, échouent quand le comportement change.

### Impact sur le reste du projet

Pour un développeur qui reprend le projet : **rien à changer dans votre code**,
les fonctions d'extraction s'appellent toujours pareil. En revanche, installez
l'option `parsing` (`pip install -e '.[parsing]'`) — sans elle vous travaillerez
en mode dégradé sans vous en rendre compte, et les formules seront abîmées.

Un seul test existant a dû être modifié (`test_ingestion.py`) : l'ajout de
l'alias `TS1` change la liste des équivalents de la série `S1`. C'est l'effet
recherché.

---

## Module 2 : Priorité au cours dans la recherche

**Le problème à résoudre.** Quand un élève demande « explique-moi les nombres
complexes », il veut un **cours**. Mais le corpus est fait aux trois quarts de
TD et d'annales : la recherche lui remonte donc des énoncés d'exercices. C'est
le principal apport de NURU sur la partie recherche.

### Ce qui a été gardé

- **Le classement RRF d'ATS, intact.** C'est le point important : on ne
  remplace pas la façon dont les résultats sont classés, on **range** le
  résultat en deux tas. Aucun calcul n'est fait sur les scores.

  > **RRF** (*Reciprocal Rank Fusion*) : méthode qui combine plusieurs
  > classements en comparant les **rangs** (1er, 2e, 3e…) plutôt que les
  > scores. On ne peut pas additionner ou pondérer ces scores : leur échelle
  > n'a pas de signification interprétable.

- **La méthode `retrieve()` existante** — inchangée. Le mode exercice continue
  de l'utiliser telle quelle : quand l'élève bloque sur un exercice, ce sont
  justement les énoncés et corrigés qu'on veut voir remonter en premier.

### Ce qui a été retiré

- **`_classify_doc_type` de NURU** — cette fonction devinait la nature d'un
  document en cherchant des mots dans son texte, **à chaque requête**. On fait
  le classement **une seule fois, à l'ingestion** : c'est plus rapide et surtout
  plus stable (le même document est toujours classé pareil).
- **Le rerangement TF-IDF de NURU** — déjà écarté par le plan : il réapprenait
  un modèle statistique sur une quarantaine de documents à chaque question.

### Ce qui a été ajouté ou modifié

**1. La taxonomie sait dire ce qui est du cours** (`config/taxonomy.py`)

Deux nouveaux types de morceaux (`solution` pour un corrigé, `exemple`), et
surtout une fonction `est_chunk_de_cours(...)` qui répond à la question « ce
morceau est-il du cours ? ».

**Elle croise deux signaux, et c'est un écart assumé avec le plan.** Le
document `ARCHITECTURE_CIBLE.md` (§3a) proposait de se fier au seul découpage
structurel : un morceau intitulé « Chapitre… » est du cours, un morceau
« Exercice… » ne l'est pas. Testé sur le corpus réel, **ça ne marche pas** :
un TD sans titres explicites est découpé par une heuristique qui produit des
« sous-notions », lesquelles passent alors pour du cours.

Mesure faite sur les 2 564 morceaux issus du dossier `exercices/` :

| Règle de classement | Morceaux de TD pris pour du cours |
|---|---|
| Découpage structurel seul (§3a du plan) | **1 922** (74 %) |
| Règle retenue (découpage **+** nature du fichier source) | **0** (0 %) |

La nature du fichier (`data/raw/exercices/…`) tranche donc en dernier ressort :
un TD ne fournit jamais de cours principal, même quand il commence par des
« rappels de cours ».

**2. Le retriever sait chercher le cours d'abord** (`vectorstore/retriever.py`)

Nouvelle méthode `retrieve_course_first()`, qui renvoie un objet
`ResultatsPedagogiques` à trois informations : le `cours`, les `complements`
(limités à 2 par défaut), et `a_du_cours` — un simple oui/non.

Elle ratisse 4 fois plus large que nécessaire avant de séparer les deux tas :
sans ce sur-échantillonnage, les premiers résultats étant souvent tous des
exercices, il ne resterait aucun cours à mettre en tête.

**3. L'agent avoue au lieu d'inventer** (`agent/graph.py`, `agent/prompt.py`)

C'est l'apport le plus important pour l'élève. Quand `a_du_cours` est faux —
le corpus n'a que des TD sur cette notion — une consigne est ajoutée au prompt :

> *« N'extrais que les éléments de cours réellement présents. Indique clairement
> que le cours complet n'est pas disponible. N'invente sous aucun prétexte le
> contenu manquant. »*

Un cours inventé est bien plus nuisible pour un élève qu'un « je ne l'ai pas ».

**4. Le chaînon manquant du module 1 a été branché** (`ingestion/pipeline.py`)

Les extracteurs de métadonnées du module 1 n'étaient appelés par personne. Ils
sont maintenant une étape à part entière du pipeline, entre la normalisation et
le découpage. L'ordre de priorité est explicite :

1. ce qu'on **devine** (nom de fichier, dossier, en-tête) — le plus faible ;
2. le **frontmatter** du document, s'il y en a un ;
3. ce qui est **saisi à la main** au téléversement — fait toujours foi.

Un paramètre `source_path` a été ajouté : lors d'une ingestion par lot depuis
le disque, le dossier parent est un indice fort que le seul nom de fichier ne
donne pas.

### Vérification faite sur les données réelles

Les 103 PDF ont été passés dans le **pipeline complet** (lecture, nettoyage,
métadonnées, découpage, annotation) :

| Dossier source | Morceaux « cours » | Morceaux « complément » |
|---|---|---|
| `cours/` | 2 943 (85 %) | 500 |
| `exercices/` | **0** | 2 564 (100 %) |

**6 007 morceaux produits, aucune erreur.** Les 500 compléments trouvés dans
`cours/` sont les exercices d'application intégrés aux polycopiés — c'est le
résultat attendu, pas une erreur de classement.

### Tests

**+18 tests** (177 → **195**, tous au vert).

### Impact sur le reste du projet

- Le mode cours et le mode exercice utilisent désormais **deux chemins de
  recherche différents**. Si vous modifiez `retrieve()`, vous ne touchez que le
  mode exercice ; pensez à `retrieve_course_first()` pour l'autre.
- `CurriculumMetadata` a un nouveau champ, `type_document` (la nature du
  fichier source). À ne pas confondre avec `type_chunk`, qui décrit un
  *morceau* de ce fichier.
- **Les documents déjà indexés doivent être ré-ingérés** pour recevoir ce
  nouveau champ. Sans cela, ils seront tous traités comme des compléments.
- Deux tests existants ont été ajustés : le pipeline compte une étape de plus
  (`metadata`), et l'alias `TS1` du module 1 modifie une liste attendue.

---

## Module 3 : Modèle de données pédagogique et rôles

**Objectif** : pouvoir suivre ce qu'un élève **maîtrise**, notion par notion —
et non plus seulement compter les exercices qu'il a faits. C'est tout l'apport
« produit » de NURU, absent du dépôt ATS.

> **Mastery learning** : approche où l'on suit le niveau de maîtrise de chaque
> notion plutôt que d'accumuler des notes. L'élève progresse notion par notion.

### Ce qui a été gardé

- **Le modèle métier de NURU** : maîtrise par notion, résultats d'exercices,
  badges, recommandations, liaison parent/enseignant → élève. C'est ce que le
  dépôt ATS n'avait pas du tout.
- **La formule de calcul de la maîtrise de NURU** — voir plus bas ; c'est un
  choix pédagogique réfléchi, pas un détail technique.
- **Le catalogue de badges de NURU** (« 🌱 Premier pas », « 🎯 Sans-faute »…),
  repris tel quel.
- **Les conventions de base de données d'ATS** : identifiants UUID, `tenant_id`
  sur chaque ligne, migrations Alembic, RLS.

  > **RLS** (*Row Level Security*) : sécurité au niveau de la ligne. La base de
  > données elle-même refuse de montrer les lignes d'un autre établissement,
  > même si le code applicatif oublie de filtrer. C'est une deuxième barrière.
  > **`tenant_id`** : l'établissement auquel appartient une donnée.

### Ce qui a été retiré

Trois tables de NURU ont été **supprimées** parce qu'elles faisaient doublon :

- **`students`** — le projet identifie déjà un élève par un `student_id`,
  présent partout (progression, conversations, journal, comptes). Une table de
  plus aurait créé deux identités concurrentes pour la même personne.
- **`interactions`** — doublonne la table `messages`, qui garde déjà l'historique
  des échanges **avec** la trace de l'orchestration.
- **`teachers`** — c'est le retrait le plus important. Chez NURU, un enseignant
  avait sa propre table, avec **son propre mot de passe**, donc *deux* chemins
  de connexion à sécuriser. Ici, un enseignant est simplement un compte avec
  `role='teacher'` : un seul chemin, un seul endroit où vérifier les droits.
  Les tables `parent_students` et `teacher_students` fusionnent de même en une
  seule table `student_links`.

- **La création de schéma par `create_all()`** — déjà écartée par le plan : elle
  ne fait jamais évoluer une table existante, donc toute mise à jour en
  production perdrait des données.

### Ce qui a été ajouté ou modifié

**1. Cinq nouvelles tables** (`persistence/models.py`)

| Table | À quoi elle sert |
|---|---|
| `concept_mastery` | Le niveau de maîtrise (0 à 1) de chaque élève sur chaque compétence |
| `exercise_results` | L'historique brut : chaque exercice ou quiz terminé |
| `badges` | Les badges débloqués |
| `recommendations` | Les révisions conseillées à un élève |
| `student_links` | Qui a le droit de consulter quel élève |

Un mot de vocabulaire : NURU dit « concept », le dépôt disait déjà
« competence » partout. C'est ce dernier qui est retenu — deux mots pour la même
chose est une source d'erreurs durable.

**2. Les règles de calcul, isolées** (`domain/mastery.py`)

Fichier de **calcul pur** : pas de base de données, pas de framework. On peut le
tester sans rien démarrer.

La formule portée de NURU est une **moyenne mobile** : à chaque tentative, on
garde 70 % du niveau acquis et on intègre 30 % du nouveau résultat. Concrètement,
les résultats récents pèsent plus que les anciens.

Pourquoi c'est le bon choix : deux élèves ont 5 échecs et 5 réussites. L'un a
d'abord échoué puis progressé, l'autre l'inverse. Une simple moyenne les
donnerait à égalité ; la moyenne mobile distingue celui qui progresse. C'est
testé explicitement.

*Contrepartie assumée* : ce score dépend de l'**ordre** des tentatives, donc on
ne peut pas le recalculer à partir des seuls compteurs. Il reste néanmoins
reconstituable, parce que chaque tentative est archivée dans `exercise_results`
— rejouer l'historique redonne exactement le même score. C'est la raison d'être
des deux tables.

**3. Six nouveaux dépôts de données** (`persistence/repositories.py`)

Ils renvoient tous des dictionnaires simples, jamais des objets de base de
données : le cœur du projet n'a pas à savoir qu'il y a du PostgreSQL derrière.

Le plus important est `StudentLinkRepository`, qui répond à la question **« ce
parent a-t-il le droit de voir cet élève ? »**. La réponse est lue en base pour
le compte **connecté** — jamais à partir d'un identifiant envoyé par le client.
C'est exactement la faille relevée chez NURU, où l'adresse
`GET /parent/students/{parent_id}` prenait l'identifiant dans l'URL et laissait
donc consulter n'importe quel parent.

**4. Deux migrations** (`migrations/versions/`)

- `0006_pedagogical_progress` — crée les cinq tables, avec RLS activée **et
  forcée** (sans « forcée », le propriétaire de la table échapperait à la règle).
- `0007_extend_roles` — les comptes acceptent désormais quatre rôles :
  `admin`, `teacher`, `parent`, `student`.

Les rôles enseignant et parent sont posés **maintenant** bien que leurs écrans
soient reportés : ajouter une valeur aujourd'hui ne coûte rien, reprendre après
coup des comptes déjà créés coûte cher.

### Vérification faite sur l'infrastructure réelle

Une base PostgreSQL 16 jetable a été démarrée pour la vérification (les
conteneurs existants n'ont pas été touchés) :

| Vérification | Résultat |
|---|---|
| Les 7 migrations s'enchaînent de zéro à jour | ✅ |
| RLS activée **et forcée** sur les 5 nouvelles tables | ✅ 5 / 5 |
| Règle d'isolation par établissement présente | ✅ 5 / 5 |
| Contrainte de rôles bien étendue aux 4 valeurs | ✅ |
| **Retour arrière** puis remontée | ✅ tables supprimées, contrainte revenue à 2 rôles, remontée sans erreur |
| Suite complète contre PostgreSQL réel | ✅ **286 tests**, 2 ignorés |

Le retour arrière mérite un mot : c'est le chemin que personne ne teste jamais,
et celui qui vous sauve un soir de mise en production ratée. Il rétrograde au
passage les comptes `teacher`/`parent` en `student` — jamais l'inverse, pour ne
pas rendre des droits par accident.

### Tests

**+40 tests** (195 → **235** hors base de données, **286** avec PostgreSQL).

### Impact sur le reste du projet

- **Une migration est à appliquer** : `alembic upgrade head`. Sans elle, tout ce
  qui touche à la maîtrise échouera.
- Un compte peut maintenant avoir le rôle `teacher` ou `parent`. Le rôle seul ne
  donne aucun droit : c'est la table `student_links` qui décide de ce qu'on voit.
- **Règle à respecter absolument** pour la suite : avant de renvoyer les données
  d'un élève à un tiers, appelez `StudentLinkRepository.can_access(...)`.
  N'acceptez jamais un identifiant d'élève venant du client.

---

## Module 4 : Quiz, vérification et suivi de la maîtrise

**Objectif** : l'agent savait expliquer et guider ; il sait maintenant
**interroger** l'élève, **vérifier** ce qu'il vient d'écrire, et **enregistrer**
ce que l'élève a réussi. C'est la boucle d'évaluation, totalement absente d'ATS.

### Ce qui a été gardé

- **La règle d'or du quiz de NURU** : *jamais de contenu factice affiché à
  l'élève*. Si le modèle n'arrive pas à produire un quiz correct, on renvoie une
  liste vide et l'interface le dit — plutôt qu'un QCM avec des propositions
  « Option 1 / Option 2 », qui donne l'illusion d'un exercice.
- **La correction d'explication incohérente**, l'idée la plus fine de NURU. Le
  modèle produit régulièrement un quiz bien formé où la bonne réponse annoncée
  est A tandis que l'explication justifie C. L'élève voit alors une correction
  qui se contredit. On reconstruit donc la phrase de correction à partir de la
  bonne réponse.
- **Les deux contrôles déterministes du vérificateur de NURU** (voir plus bas).
- **Toute la branche exercice et toute la branche cours d'ATS**, intactes.

### Ce qui a été retiré

- **`_check_coherence` et `_check_hallucinations` de NURU** — écartés, comme le
  prévoyait le plan. Le premier notait la « cohérence » d'une réponse en
  comptant les mots « donc », « ainsi », « en effet ». Un texte **faux** truffé
  de connecteurs obtenait une bonne note ; un texte juste et concis, une
  mauvaise. Une mesure qui ne mesure pas ce qu'elle annonce est pire que pas de
  mesure : elle donne une confiance injustifiée.
- **Le fournisseur codé en dur** — le prompt de NURU commençait par « Tu es
  Gemini ». Le projet route vers plusieurs fournisseurs de modèles ; la consigne
  ne peut pas en désigner un.
- **Le niveau codé en dur** — NURU écrivait « niveau Terminale S1 » dans le
  prompt. Le cadre curriculaire est maintenant passé en paramètre.
- **Les questions ouvertes de repli** — NURU proposait « Définis X en tes
  propres mots » quand il ne savait pas faire mieux. Ce sont des questions
  qu'on ne peut pas corriger automatiquement : elles n'alimentent donc pas la
  maîtrise, et donnent l'illusion d'une évaluation.

### Ce qui a été ajouté ou modifié

**1. Une troisième posture : le quiz** (`agent/intent.py`, `agent/graph.py`)

L'agent avait deux postures ; il en a trois :

| Posture | Ce que fait l'agent |
|---|---|
| **Exercice** (défaut) | Guide par indices progressifs, sans donner la réponse |
| **Cours** | Expose un chapitre, section par section |
| **Quiz** *(nouveau)* | Interroge l'élève et corrige |

La règle de sûreté est conservée : **toute intention non reconnue retombe sur
« exercice »**, la posture qui ne dévoile rien. Et la reconnaissance du quiz est
volontairement étroite (« teste-moi », « fais-moi un quiz », « QCM »…) : on
n'interroge jamais quelqu'un qui n'a rien demandé.

Une demande de quiz **interrompt** un cours en cours : « teste-moi » au milieu
d'une leçon veut dire « interroge-moi maintenant », pas « continue ».

**2. Deux nouvelles étapes en fin de parcours** (`agent/graph.py`)

Tous les tours passent désormais par deux étapes finales :

- **`verify_response`** — les contrôles déterministes (ci-dessous), plus la
  validation du JSON pour un quiz ;
- **`persist_progression`** — met à jour la maîtrise, *si* le tour porte un
  résultat mesurable.

Ce « si » est important : poser une question ne prouve rien. Seul un **résultat
corrigé** (`exercise_outcome`) fait bouger la maîtrise. Sans lui, l'étape ne
fait rien — et c'est voulu, c'est même testé.

Ces deux étapes ne vivent **que** dans le parcours complet, pas dans le
streaming : en affichage progressif, la réponse est produite hors du graphe.

**3. Deux contrôles factuels** (`agent/verify.py`)

Fichier de calcul pur : aucun appel au modèle, donc aucun coût ni délai.

- **Le niveau du vocabulaire.** Si la réponse parle de « dérivées partielles »
  ou de « gradient » alors que la compétence traitée est à une seule variable,
  le modèle est sorti du programme du secondaire. Signal fiable.
- **La fidélité au calcul.** Quand l'outil de calcul symbolique a produit un
  résultat exact, ce résultat **doit** apparaître tel quel dans la réponse.
  Sinon, c'est que le modèle a refait le calcul de son côté — et il se trompe
  régulièrement. C'est le plus utile des deux.

**4. La génération de quiz** (`agent/quiz.py`)

Deux essais maximum, puis on abandonne honnêtement. Chaque réponse du modèle est
passée au crible : JSON extractible ? question présente ? au moins deux
propositions ? la bonne réponse désigne-t-elle une proposition qui existe ? pas
de texte de remplissage ? Un seul « non » et la réponse est rejetée — il n'y a
pas de réparation partielle, un quiz à moitié valide est un quiz faux.

La **correction**, elle, est purement déterministe : on compare deux
identifiants, aucun modèle n'intervient. Un élève ne doit jamais voir sa réponse
jugée différemment d'une fois à l'autre.

**5. Deux nouveaux ports** (`agent/ports.py`)

`MasteryPort` et `EvaluationPort`, avec leurs versions en mémoire pour les
tests. Point important : la version en mémoire et la version PostgreSQL
appellent **le même** fichier de calcul (`domain/mastery.py`). Un test
hors-ligne mesure donc le vrai comportement, pas une approximation.

### Tests

**+55 tests** (235 → **290** hors base de données, **341** avec PostgreSQL).

### Impact sur le reste du projet

- `TutorAgent` accepte un port de maîtrise supplémentaire (facultatif — sans
  lui, la maîtrise n'est simplement pas suivie).
- `respond()` accepte `exercise_outcome`, et son résultat expose trois champs
  nouveaux : `verification`, `quiz`, `mastery`.
- Le streaming SSE et les deux postures existantes sont **inchangés** : aucun
  test existant n'a eu à être modifié dans ce module.
- Si vous ajoutez une posture, pensez à `_route_by_intent` — et gardez
  « exercice » comme défaut.

---

## Module 5 : Les routes de l'API pédagogique

**Objectif** : rendre utilisables depuis l'extérieur les briques construites aux
modules 3 et 4 — générer un quiz, le corriger, consulter la progression — **sans
rouvrir la faille de NURU**.

### Ce qui a été gardé

- **Le périmètre fonctionnel de NURU** : quiz, correction, historique,
  progression. C'est ce que le dépôt ATS n'exposait pas.
- **Les conventions d'API du projet** : chaque route derrière une dépendance
  d'authentification, chaque réponse décrite par un modèle typé (jamais un
  dictionnaire brut), une session de base par requête.

### Ce qui a été retiré

- **`GET /parent/students/{parent_id}` et ses semblables** — non portées.
  Chez NURU, l'identifiant venait de l'URL : n'importe qui pouvait consulter
  n'importe quel parent. Ici, **l'identité vient toujours du jeton**.
- **Les routes `/teacher` et `/parent`** — reportées en v1.1, conformément à la
  décision de cadrage. Le modèle de données est posé, les écrans viendront.
- **`POST /chat/simple`** — le chemin de débogage parallèle de NURU, déjà écarté
  par le plan.

### Ce qui a été ajouté ou modifié

**1. La règle d'accès, écrite une seule fois** (`api/dependencies.py`)

`ensure_can_access_student()` répond à « ce compte peut-il voir les données de
cet élève ? ». Trois cas, et rien d'autre :

| Rôle | Ce qu'il voit |
|---|---|
| **admin** | Tous les élèves de son établissement |
| **élève** | Lui-même, uniquement |
| **enseignant / parent** | Seulement les élèves qui lui sont rattachés en base |
| *(rôle inconnu)* | **Rien** — le refus est le défaut |

Elle est centralisée parce qu'une règle recopiée dans dix routes finit toujours
par diverger dans l'une d'elles — et c'est celle-là qui devient la faille.

> ⚠️ **Un correctif important au passage.** L'ajout des rôles au module 3 avait
> ouvert une brèche : l'ancien contrôle de `/api/progression` disait « si ce
> n'est pas un élève, laisse passer ». Tant qu'il n'existait que `admin` et
> `student`, c'était juste. Avec `teacher` et `parent`, **un parent pouvait
> consulter n'importe quel élève**. Refermé, et couvert par des tests.

**2. Trois nouveaux jeux de routes**

| Route | Ce qu'elle fait |
|---|---|
| `POST /api/quiz` | Génère un quiz sur une compétence |
| `POST /api/quiz/answer` | Corrige, enregistre le résultat, met à jour la maîtrise, attribue les badges |
| `GET /api/evaluation/{eleve}` | Historique des exercices et quiz |
| `GET /api/mastery/{eleve}` | Niveau par compétence, priorités de révision, badges |

**3. La bonne réponse ne descend plus dans le navigateur**

C'est le point le plus important du module, et il n'était pas prévu au plan.

NURU renvoyait le quiz complet au navigateur, **bonne réponse incluse**. Un
élève qui ouvre les outils de développement (F12) la lit avant de répondre :
l'évaluation ne mesure plus rien.

Désormais, `POST /api/quiz` renvoie la question et les propositions, mais la
correction voyage **scellée** dans un jeton signé (`quiz_token`) que le client
transporte sans pouvoir le lire ni le modifier. `POST /api/quiz/answer` le
rouvre côté serveur. Un jeton bricolé est rejeté — c'est testé.

Cette solution ne demande **aucune table supplémentaire**. L'alternative
(stocker les quiz en base) est décrite au point V6 ci-dessous.

**4. Un quiz absent n'est pas une erreur**

Quand le modèle ne produit rien d'exploitable, la route répond `200` avec
`available: false` et un message à afficher — pas une erreur technique.
L'interface dit honnêtement « réessaie », plutôt que de montrer un
questionnaire de remplissage. C'est la règle du module 4, remontée jusqu'à l'API.

**5. Deux petits alignements**

- La création de compte accepte les **quatre rôles** ; l'API en refusait encore
  deux alors que la base les acceptait depuis la migration `0007`.
- `TutorAgent` expose son modèle de langage (`agent.llm`), pour que la
  génération de quiz utilise **la même chaîne de repli** que le chat.

**6. Le contrat pour le frontend** (`scripts/export_openapi.py`)

```bash
python scripts/export_openapi.py            # -> openapi.json (21 chemins)
npx openapi-typescript openapi.json -o src/types/api.d.ts
```

Générer les types plutôt que les écrire à la main : renommer un champ côté API
casse alors la compilation du frontend, au lieu de produire un `undefined`
silencieux en production. C'est le mécanisme qui empêchera les deux moitiés du
projet de re-diverger.

### Une étape du plan qui s'est révélée sans objet

Le plan prévoyait de « brancher les ports pédagogiques sur le chat ». Vérification
faite, `/api/chat` fonctionne **uniquement en streaming** : il s'arrête avant les
étapes finales du graphe, et ne touche donc jamais à la maîtrise. C'est la route
`/api/quiz/answer` qui la met à jour. Rien à brancher — mieux vaut le dire que
d'ajouter un câblage inutile.

### Tests

**+27 tests d'API** (359 → **386** avec PostgreSQL ; inchangé à 290 sans base,
ces tests exigeant PostgreSQL).

Dont, en particulier :

- un test **401 sans jeton** sur les 10 routes métier — le garde-fou qui
  manquait totalement à NURU ;
- des tests **403** par rôle : élève sur un autre élève, parent non rattaché,
  rattachement d'un autre établissement, rôle inconnu ;
- la preuve que la bonne réponse **n'est pas** dans la réponse HTTP.

### Impact sur le reste du projet

- **Règle à respecter pour toute nouvelle route** touchant les données d'un
  élève : appeler `ensure_can_access_student(...)`. Ne jamais se fier à un
  identifiant fourni par le client.
- Le frontend devra envoyer `quiz_token` tel quel à la correction — il ne doit
  ni le lire, ni le construire.
- Le schéma OpenAPI a changé : régénérez les types côté frontend.

---

## ⚠️ Points à valider

*Ces questions sont apparues pendant la fusion et ne sont pas tranchées par le
plan initial. Elles attendent une décision d'équipe — le code n'a pas été
modifié dans un sens ou dans l'autre.*

### V1 — 57 % du corpus serait invisible à une recherche filtrée par série

**Le constat, mesuré.** Sur les 103 PDF, la série reconnue se répartit ainsi :

| Série détectée | Nombre de documents |
|---|---|
| `S1` (exploitable) | 41 |
| `S` (ambigu) | 25 |
| aucune | 30 |
| `TS` (ambigu) | 4 |
| `S2` | 2 |
| `C` (ambigu) | 1 |

Or le filtre de recherche actuel **exclut** un document dont la série ne
correspond pas exactement — et il exclut aussi ceux dont la série est *vide*.
Vérifié en exécutant le filtre :

```
chunk sans série  -> retenu ? False
chunk série 'S'   -> retenu ? False
chunk série 'S1'  -> retenu ? True
```

Autrement dit, **59 documents sur 103** disparaîtraient d'une recherche
filtrée sur « S1 ». C'est exactement le mode de panne déjà rencontré et
documenté dans le projet (« un filtre exact coupait l'élève de 92 % du corpus,
silencieusement »).

**D'où viennent les `S` ?** De documents qui portent « Classe : Terminale S » —
la notation **française**, pas sénégalaise. En regardant les auteurs
(`G. COSTANTINI`, `Jérôme ONILLON`), une partie du dossier `cours/` est
constituée de polycopiés français, pas du programme sénégalais.

**Trois options :**

| Option | Effet | Risque |
|---|---|---|
| **A.** Une série absente ou ambiguë n'exclut plus le document | Les 59 documents redeviennent trouvables | Un élève de Seconde peut voir du contenu de Terminale |
| **B.** Décider que « Terminale S » = `S1` | Récupère 25 documents | Faux si certains visent S2 |
| **C.** Ne rien changer | — | Plus de la moitié du corpus reste invisible |

**Mon avis** : **A**, parce qu'un document trouvable mais un peu hors-sujet est
un moindre mal qu'un document introuvable, et parce que c'est cohérent avec la
doctrine déjà retenue dans le projet sur le filtrage curriculaire. Mais cela
touche la règle de filtrage (décision D5 du comparatif) : à confirmer en équipe.

**Question ouverte au-delà du code** : les polycopiés français ont-ils leur
place dans un tuteur du programme sénégalais ? Cela rejoint la question Q3
(droits d'usage du corpus).

### V2 — Faut-il porter `NougatAdapter` ?

Le plan le prévoyait « en option ». Il n'a **pas** été porté, pour une raison
précise : l'implémentation de NURU ne fonctionne pas. Elle appelle
`NougatModel.from_pretrained(...)` puis `model.predict(chemin)`, qui ne
correspond pas à l'interface réelle de la bibliothèque Nougat ; et comme
`nougat` n'est installé nulle part, le code retombait **toujours** sur PyMuPDF
sans que personne ne s'en aperçoive.

**Mon avis** : ne pas porter du code mort. PyMuPDF donne déjà de bons résultats
(vérifié sur les 103 PDF). Si la qualité des formules devient insuffisante, on
rouvrira le sujet avec une vraie évaluation — le point d'extension est prêt
dans `loaders/pdf.py`. **À confirmer.**

### V3 — Que faire de la ligne « Compétences » des documents ?

Les documents contiennent souvent une ligne du type
`Compétences : Calculer, Déterminer, Résoudre`. NURU la rangeait dans un champ
`competences`.

Le projet possède déjà un champ `competence`, mais il désigne autre chose : une
**compétence du programme** (ex. « Dériver une fonction »), utilisée pour
filtrer les recherches. Y ranger une liste de verbes d'action dégraderait le
filtrage.

La liste est donc extraite et conservée, mais elle n'alimente pas le champ
`competence`. **À confirmer** : faut-il la découper en verbes séparés et s'en
servir pour autre chose (par exemple étiqueter le type d'exercice), ou
simplement l'ignorer ?

---

### V4 — Le jeu d'évaluation de recherche n'existe pas (étape sautée)

**À signaler franchement** : l'étape P1.4 du plan — construire 30 à 50 questions
d'élèves réelles avec le chapitre attendu, et mesurer le `recall@5` — **n'a pas
été faite**, parce qu'elle demande des questions d'élèves réelles que je ne peux
pas inventer sans fausser la mesure.

> **`recall@5`** : sur 5 documents remontés, la part de fois où le bon document
> s'y trouve. C'est la mesure de base de la qualité d'une recherche.

**Conséquence directe** : l'étape P2.4 (« conserver le re-ranker seulement s'il
améliore le taux de *cours en tête* sans dégrader le `recall@5` ») n'a pas pu
être appliquée. Ce qui est prouvé aujourd'hui :

- ✅ le **classement** cours/complément est juste (mesuré : 0 faux positif sur
  2 564 morceaux de TD) ;
- ❌ le fait que remonter le cours en tête **améliore réellement les réponses**
  n'est pas mesuré — c'est une hypothèse raisonnable, pas un résultat.

Le plan lui-même le dit : *« sans cette mesure, tous les arbitrages RAG
resteront des opinions invérifiables. »* C'est le point le plus important à
programmer, et il demande une contribution humaine (un enseignant, ou les
questions réellement posées par des élèves).


### V5 — Une bonne explication de quiz peut être jetée

Règle portée de NURU : l'explication produite par le modèle n'est conservée que
si elle **cite littéralement** le texte de la bonne proposition, et aucune autre.

Sur cet exemple, l'explication « On applique la formule de dérivation des
puissances » est juste et utile, mais elle ne contient pas la chaîne « $2x$ » :
elle est donc **écartée**, et l'élève ne voit que « La bonne réponse est A :
$2x$. »

| Option | Effet | Risque |
|---|---|---|
| **A.** Garder la règle de NURU | Aucune explication contradictoire ne passe | On perd des explications correctes et utiles |
| **B.** Ne rejeter que si l'explication cite une **autre** proposition | On garde les explications génériques mais justes | Une explication vague pourrait passer |

**Mon avis** : **B**. Le danger qu'on cherche à écarter est une explication qui
justifie *une autre* réponse. Une explication qui ne cite aucune proposition
n'est pas contradictoire, juste générale — et elle apporte quand même quelque
chose à l'élève.

Le comportement actuel est celui de NURU (option A), inchangé, et un test le
documente explicitement. **À confirmer avant de le modifier**, car cela touche
ce que voit l'élève.


### V6 — Faut-il persister les quiz en base ?

La bonne réponse voyage aujourd'hui **scellée dans un jeton signé**, valable une
heure. Ça marche, c'est sûr, et ça n'a demandé aucune table.

L'alternative serait de **stocker chaque quiz généré** dans une table, et de ne
renvoyer au client qu'un identifiant.

| | Jeton signé (retenu) | Table de quiz |
|---|---|---|
| Table supplémentaire | non | oui (+ migration) |
| Réponse protégée | oui | oui |
| Rejouer un quiz plus tard | non | oui |
| Savoir quelles questions ont été posées | non | oui |
| Repérer une question mal formulée (tout le monde se trompe) | non | **oui** |

**Mon avis** : garder le jeton pour l'instant — il répond au besoin immédiat
sans alourdir le modèle. Mais si vous voulez un jour **analyser la qualité des
questions générées** (repérer celles où tous les élèves échouent, signe d'une
question ambiguë), il faudra la table. C'est une décision produit, pas
technique : **à trancher en équipe**.

