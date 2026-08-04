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

