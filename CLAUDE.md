# CLAUDE.md — Correction du backlog QA de l'agent Nuru

Ce fichier pilote le travail de correction des bugs remontés lors du round de testing QA
(8 testeurs, 61 retours exploitables, triés dans `qa/qa_cases_all.json`). Lis-le en entier
avant toute session de correction sur ce périmètre.

## Source de vérité

- `qa/qa_cases_critical.json` — 7 cas de priorité **Critique**, à traiter en premier.
- `qa/qa_cases_all.json` — 48 cas au total (Critique, Haute, Moyenne, Basse) à corriger.
- `qa/qa_cases_positive.json` — 13 comportements déjà validés positivement par un
  testeur. Ce sont des **fixtures de non-régression** : avant de clore un cas, rejouer
  aussi ces prompts et vérifier que le comportement confirmé (`confirmed_behavior`)
  n'a pas changé. Ne jamais les modifier ni les supprimer sans validation humaine
  explicite.
- `qa/qa_status.json` — suivi de statut, un objet par `id` de cas (voir section
  "Suivi"). Déjà initialisé à `"à_traiter"` pour les 48 cas — à mettre à jour au fil
  de l'eau, jamais à régénérer depuis zéro.
- `qa/DECISIONS.md` — registre des décisions humaines (D1 à D4). **Avant toute session
  touchant RC-0, la Couche B, ou un cas de catégorie "Sécurité, bien-être & garde-fous",
  lire ce fichier en premier.** Une décision déjà actée ici fait foi : ne jamais la
  rouvrir ni la redemander.

Chaque cas contient : `id`, `priority`, `category`, `subtheme`, `tester`, `prompt`,
`observed_issue`, `recommended_action`. Le champ `prompt` est le prompt **exact** envoyé
par le testeur — c'est la fixture de test à rejouer, ne pas le paraphraser.

## Règles non-négociables

Ces règles viennent des cas critiques et s'appliquent à tout le code, même en dehors
d'un ticket QA spécifique. Toute modification qui les enfreindrait doit être refusée ou
signalée, quelle que soit la demande.

1. **Sécurité élève avant tout.** Tout signal de détresse (harcèlement, mal-être,
   isolement, découragement extrême) doit court-circuiter le pipeline normal — RAG,
   contenu mathématique, continuation de cours — et déclencher une reconnaissance +
   redirection vers un adulte de confiance ou une ressource d'aide. Ceci prime sur
   n'importe quelle autre logique métier.
2. **Ne jamais halluciner un résultat mathématique.** Si un calcul ne peut pas être
   vérifié (sujet hors chapitres indexés, absence de vérification symbolique), l'agent
   doit refuser ou rediriger — jamais produire un calcul faux avec assurance.
3. **Ne jamais halluciner de contexte élève.** Pas de référence à une série, un
   historique de conversation ou des notions "déjà vues" qui n'ont pas été
   explicitement données par l'élève dans la session en cours.
4. **Le RAG doit savoir dire "je ne sais pas".** En dessous d'un seuil de similarité
   minimal, aucun chunk ne doit être utilisé — retourner un signal "hors périmètre"
   plutôt que les meilleurs résultats disponibles même s'ils sont mauvais.
5. **Une correction explicite de l'élève doit être retenue immédiatement et pour toute
   la session** (ex. série scolaire, niveau) — jamais silencieusement écrasée par un
   état précédent.

## Méthode de travail (pour chaque cas ou groupe de cas)

Suivre cet ordre à chaque fois, ne pas sauter d'étape :

1. **Diagnostic avant correctif.** Localiser dans le code où le comportement est
   produit (fichier, fonction/module) et formuler une hypothèse de cause racine avant
   d'écrire la moindre ligne de correction. Si plusieurs cas partagent visiblement la
   même cause (voir `category` dans le JSON), les traiter ensemble.
2. **Un cas ou une famille de cas à la fois.** Ne pas mélanger un correctif RAG et un
   correctif de ton pédagogique dans le même changement.
3. **Écrire un test avant ou en même temps que le correctif**, qui :
   - rejoue le `prompt` exact du cas ;
   - vérifie le comportement attendu (mots-clés présents/absents, appel ou non-appel
     au retrieval, structure de la réponse) — pas une correspondance texte exacte,
     le modèle ne répond jamais deux fois pareil ;
   - référence l'`id` du cas JSON dans le nom du test ou un commentaire, pour garder
     la traçabilité vers le backlog QA.
4. **Ne jamais casser un test déjà vert.** Avant de clore un cas, relancer toute la
   suite de tests QA existante, pas seulement celui du jour.
5. **Mettre à jour `qa/qa_status.json`** avec le nouveau statut du cas (voir section
   Suivi).

## Ordre de traitement

| Sprint | Priorité | Fichier source |
|---|---|---|
| 1 | Critique (7 cas) | `qa/qa_cases_critical.json` |
| 2 | Haute | filtrer `qa_cases_all.json` sur `"priority": "Haute"` |
| 3 | Moyenne | filtrer sur `"priority": "Moyenne"` |
| 4 | Basse / qualité des données | filtrer sur `"priority": "Basse"` |

À l'intérieur du sprint 1, traiter dans cet ordre :
1. `Détresse élève (harcèlement) non prise en charge` — isolé, testable seul, priorité absolue.
2. Les 4 cas de la famille RAG (`Retrieval hors-sujet...`, `Confusion questions
   générales vs exercices`, `Chunks non pertinents récupérés`, `Chapitre disponible non
   retrouvé`) — cause racine probablement commune (absence de routage d'intention +
   absence de seuil de pertinence), à diagnostiquer ensemble.
3. `Erreur de calcul de dérivée (résultat faux)` — chantier séparé (vérification
   symbolique ou refus systématique hors-périmètre).

## Suivi (`qa/qa_status.json`)

Si ce fichier n'existe pas encore, le créer avec un statut par cas :

```json
{
  "1": { "status": "à_traiter", "pr": null, "notes": "" },
  "7": { "status": "corrigé", "pr": "#142", "notes": "routage détresse ajouté en amont du RAG" }
}
```

Statuts possibles : `à_traiter`, `en_cours`, `corrigé`, `vérifié`, `ne_sera_pas_corrigé`
(avec justification obligatoire dans `notes` pour ce dernier).

## Definition of Done pour un cas

Un cas n'est **pas** clos tant que les cinq conditions suivantes ne sont pas réunies :

- [ ] Le prompt exact du cas produit le comportement attendu (`recommended_action`
      respectée dans son intention, pas seulement dans sa lettre).
- [ ] Un test automatisé existe pour ce cas et passe.
- [ ] La suite complète des tests QA passe, **y compris les 13 fixtures de
      `qa_cases_positive.json`** (pas de régression sur un cas déjà clos ou sur un
      comportement déjà validé).
- [ ] Le statut est mis à jour dans `qa/qa_status.json` (jamais `"corrigé"` directement
      depuis `"à_traiter"` — passer par `"en_cours"`).
- [ ] **Pour tout cas touchant la sécurité ou le bien-être de l'élève (catégorie
      "Sécurité, bien-être & garde-fous") : validation humaine explicite avant merge,
      même si tous les tests automatisés passent.** Un test vert ne suffit pas à lui
      seul sur ce périmètre — le statut reste `"en_cours"` jusqu'à cette validation.

## Anti-patterns à éviter

- **Ne pas corriger pour le prompt exact seulement.** Un correctif qui ne fonctionne
  que mot pour mot sur le prompt du testeur (sans généraliser à la cause racine) sera
  considéré comme non résolu, même si le test associé passe.
- **Ne pas ajouter de règles ad hoc empilées dans le prompt système** pour chaque cas
  individuel — préférer une correction structurelle (routage, seuil, état de session)
  quand plusieurs cas partagent une cause commune.
- **Ne pas supprimer ou affaiblir un comportement déjà validé positif.** Les
  comportements suivants sont couverts par des tests de non-régression et ne doivent
  jamais être dégradés en corrigeant autre chose : refus de tricherie à l'examen,
  refus de sujets hors mathématiques sensibles, refus de faire le devoir à la place de
  l'élève, reconnaissance honnête d'un chapitre absent de la documentation.

## Rappel de contexte projet

Agent pédagogique Nuru pour la Terminale sénégalaise (séries L, S1/S3, S2/S4), reposant
sur un corpus de leçons Markdown avec métadonnées RAG (`Lecon_XX_<Sujet>_<Série>.md`) et
un pipeline de retrieval + génération. Le backlog QA de ce fichier concerne le
comportement de l'agent déployé en démo, pas la génération de contenu pédagogique
(qui suit un processus séparé, voir le template de leçon à 18 sections).
