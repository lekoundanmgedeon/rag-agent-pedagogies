# ADR 0003 — Mistral primaire + Ollama fallback + mock

## Contexte

Le public cible (élèves sénégalais, potentiellement mineurs) exige un service
LLM disponible et un filet de sécurité en cas d'indisponibilité réseau/API, sans
jamais bloquer la démonstration ou le développement local.

## Décision

Chaîne de fallback `FallbackRouter` : Mistral (API externe) → Ollama (local,
souverain) → Mock (déterministe, toujours disponible). Composition dynamique
selon la configuration disponible (`build_router`) :
- clé Mistral présente → `[Mistral, Ollama, Mock]` ;
- sinon Ollama joignable → `[Ollama, Mock]` ;
- sinon → `[Mock]`.

## Justification

- **Qualité** : Mistral (modèle hébergé, à jour) donne la meilleure qualité de
  réponse pédagogique.
- **Souveraineté/résilience** : Ollama local sert de repli sans dépendance à un
  service tiers — pertinent pour un contexte où la connectivité ou la
  confidentialité des données d'élèves mineurs peut être une préoccupation.
- **Jamais bloquant** : le mock termine toujours la chaîne — un développeur ou
  un testeur peut faire tourner l'intégralité du système sans aucune clé API
  ni serveur Ollama.
- Bascule **silencieuse** à l'erreur (`LLMError`) : l'élève ne voit jamais une
  erreur technique, juste une réponse (éventuellement du fournisseur suivant).

## Conséquences

- Trois implémentations `BaseLLM` à maintenir, mais un contrat commun
  (`generate`/`generate_stream` async) qui les rend interchangeables.
- En streaming, un échec **après** le premier token n'est pas rejouable (le
  flux vers le client a déjà commencé) — propagé tel quel plutôt que silencieux.
- Le mock, bien que déterministe et clairement étiqueté « mode démonstration »
  dans sa réponse, ne doit jamais être pris pour une vraie réponse pédagogique
  en production — supervision via `GET /health` (`llm: [...]`).
