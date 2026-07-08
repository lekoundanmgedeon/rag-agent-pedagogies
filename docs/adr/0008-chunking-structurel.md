# ADR 0008 — Chunking structurel (jamais taille fixe)

## Contexte

Un chunking par taille fixe (ex. 512 tokens avec chevauchement) est simple mais
peut couper un exercice en plein milieu de l'énoncé, séparer l'indice de la
solution, ou fragmenter une compétence en morceaux incohérents — dégradant la
pertinence du RAG précisément sur le cas d'usage le plus sensible pédagogiquement
(un exercice d'annale doit remonter **entier**, indice et solution compris).

## Décision

Chunking par **structure pédagogique** : un chunk = une compétence complète,
un chapitre, ou un exercice entier (indivisible). Détection par marqueurs
(`## ` pour chapitre/compétence, `### Exercice` pour un exercice) sur le format
pivot, avec repli sur une heuristique de détection de titres numérotés pour un
texte sans marqueurs (`ingestion/chunking.py`).

## Justification

- L'exercice indivisible est une exigence métier explicite : la récupération
  pré-réponse doit remonter le trio énoncé+indice+solution ensemble, sinon le
  tuteur ne peut pas s'appuyer dessus de façon cohérente pour guider l'élève.
- Le découpage suit la sémantique du contenu plutôt qu'une métrique de taille
  arbitraire : un chapitre court reste un chunk, un long exercice avec plusieurs
  questions reste un chunk (pas de coupure artificielle).
- L'heuristique de repli (titres numérotés, mots-clés « Chapitre »/« Exercice »)
  couvre le cas réaliste d'un PDF extrait sans structure Markdown propre,
  fréquent avec des documents scannés/anciens.

## Conséquences

- Les chunks ont une taille **variable**, parfois importante (un exercice long
  avec plusieurs sous-questions) — le prompt assemblé (`agent/prompt.py`)
  tronque les extraits au-delà de 600 caractères pour rester dans un budget de
  contexte raisonnable, au prix d'une troncature visible pour les tuteurs très
  longs (compromis assumé).
- Un document sans aucune structure détectable (ni marqueurs, ni titres
  numérotés) devient un **unique** chunk couvrant tout le fichier — dernier
  recours, à éviter en pratique en structurant le corpus source.
