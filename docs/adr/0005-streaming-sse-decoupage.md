# ADR 0005 — Streaming SSE avec découpage préparation/génération

## Contexte

`POST /api/chat` doit renvoyer le niveau d'indice, les sources RAG et l'outil
utilisé **avant** la réponse complète (pour que l'interface affiche ces
méta-informations immédiatement), puis streamer la génération token par token
pour une latence perçue minimale.

## Décision

Le graphe LangGraph est compilé en **deux variantes** partageant les mêmes
nœuds : un graphe de préparation (nœuds a→e, sans génération) et un graphe
complet (a→f). `TutorAgent.prepare()` exécute le premier et renvoie un objet
`Prepared` (prompt assemblé + trace) ; `TutorAgent.stream()` prend ce `Prepared`
et appelle `generate_stream()` séparément.

## Justification

- Sépare clairement ce qui est **rapide et synchrone** (retrieval, détection de
  frustration, diagnostic d'indice, routage d'outil, garde-fous — tout en CPU/
  I/O local ou Qdrant) de ce qui est **lent et streamé** (l'appel LLM).
- Permet à l'API d'émettre l'événement SSE `{meta: ...}` dès que `prepare()`
  retourne, sans attendre le premier token du LLM.
- Le même `Prepared` sert aussi à `respond()` (tour complet non-streamé, utile
  pour les tests et la démo hors-ligne) — aucune duplication de logique entre
  chemin streamé et non-streamé.

## Conséquences

- Deux graphes compilés par instance de `TutorAgent` (léger : mêmes fonctions
  de nœud, juste deux assemblages d'arêtes différents).
- La persistance de la conversation (messages) a lieu **après** la fin du flux
  de tokens mais **avant** l'événement `done` (qui transporte le `message_id`
  fraîchement créé) — documenté dans `docs/api.md` pour éviter toute confusion
  sur le sens de « non-bloquant » ici (non-bloquant *pour le token-par-token*,
  pas totalement déconnecté du cycle requête/réponse).
