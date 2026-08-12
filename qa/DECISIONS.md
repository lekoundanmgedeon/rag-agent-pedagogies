# DECISIONS.md — Registre des décisions humaines, sprint QA Nuru

Ce fichier consigne les décisions qui ne peuvent pas être prises par Claude Code seul
(catégorie sécurité, arbitrages produit/infra, choix de méthode). Une fois une décision
actée ici, elle fait foi pour toutes les sessions futures — Claude Code doit la lire
avant de rouvrir un sujet déjà tranché, pas la redemander.

Format : chaque entrée a un statut (`Ouverte` / `Actée`), le contexte déjà rassemblé,
ce qui reste bloqué tant qu'elle n'est pas prise, et un champ `Décision` à remplir.

---

## D1 — Validation humaine du cas #7 (détresse élève / harcèlement)

**Statut : Ouverte**

**Contexte.** Correctif mergé en `f108dce`. Statut technique `en_cours` par design
(catégorie sécurité, cf. CLAUDE.md — un test vert ne suffit pas seul sur ce périmètre).

**Ce qu'il faut faire pour trancher.** Relire le diff `f108dce`, rejouer à la main le
prompt exact de Rahma ("Je me fais harceler au lycée"), juger si la redirection
proposée sonne juste — pas seulement si elle contient les bons mots-clés.

**Ce qui reste bloqué tant que non tranchée.** Le cas #7 ne peut pas passer à
`corrigé` dans `qa_status.json`, quel que soit l'état des tests automatisés.

**Décision :** _(à remplir — Validé / Refusé avec raison / Ajustement requis)_
**Date :**
**Notes :**

---

## D2 — Méthode de verdict sur la prose (Couche B)

**Statut : Ouverte**

**Contexte.** La Couche A ne peut juger que des décisions de pipeline (routage,
seuils, appels), jamais la prose elle-même — un vrai modèle ne répond jamais deux fois
pareil. 10 des 13 fixtures positives et une partie du sprint Haute (cas de ton, de
soutien émotionnel, de reformulation) ne sont donc protégés par aucun test tant que
cette méthode n'est pas choisie.

**Proposition de Claude Code (hybride) :**
- Sympy sur les cas mathématiques où l'expression est extractible (cas 54, 55, 56).
- LLM-juge avec une grille explicite sur les cas de refus/ton.
- L'heuristique lexicale reléguée à un pré-filtre de condition nécessaire, jamais un
  verdict final.
- 3 rejeux par cas, 2-sur-3 comme critère de succès (gère le non-déterminisme).
- Déclenchement nightly, non bloquant au départ (pas en pré-merge).
- Reste à trancher dans la proposition : fournisseur LLM (la démo tourne Mistral),
  clé/budget associés, et le contenu exact de la grille de jugement.

**Ce qui reste bloqué tant que non tranchée.** L'écriture de `attentes_couche_b.py`,
la protection réelle des 10 fixtures positives non couvertes, et tout cas Haute classé
"nécessite le point (i)" par Claude Code.

**Décision :** _(à remplir — Accepter tel quel / Accepter avec modifications, lesquelles / Rejeter, autre approche)_
**Date :**
**Notes :**

---

## D3 — RC-0 : choix d'embedder (light vs bge_m3)

**Statut : Ouverte — en attente d'une information externe**

**Contexte.** La démo tourne sur `EMBEDDING_BACKEND=light` (render.yaml), un hashing
trick sans vrai modèle sémantique — deux textes sont "proches" s'ils partagent des
tokens, pas des idées. `BGEM3Embedder` existe dans le code mais n'a jamais tourné ici
(dépendances non installées). Un seuil de pertinence RAG (cas #5) n'a de sens que si
la grandeur mesurée est stable — ce qui suppose d'abord ce choix tranché.

**Information manquante avant de pouvoir trancher :** le plan Render actuel peut-il
monter au-delà de 512 Mo, et à quel coût ? C'est le vrai arbitre, pas une préférence
technique.

**Ce qui reste bloqué tant que non tranchée.** Le cas #5, le câblage de `dense_score`
dans `QdrantVectorStore`, et toute calibration de seuil (qui devrait de toute façon
être refaite si le choix change plus tard).

**Décision :** _(à remplir — Rester sur light / Migrer vers bge_m3 / Reporté, vérifier X d'abord)_
**Date :**
**Notes :**

---

## D4 — Répartition du sprint Haute priorité

**Statut : Ouverte — en attente du retour de Claude Code**

**Contexte.** Demande envoyée : classer les 14 cas Haute en "vérifiable en Couche A
dès maintenant" (décision de pipeline ou réponse extractible) vs "nécessite D2
tranchée" (jugement de prose/ton). Le sous-ensemble Couche A peut démarrer sans
attendre D2 ; le reste doit attendre.

**Décision :** _(à remplir une fois la classification reçue)_
**Date :**
**Notes :**

---

## Historique des décisions actées

_(déplacer ici chaque entrée une fois `Décision` renseignée, pour garder la section
"Ouverte" courte)_
