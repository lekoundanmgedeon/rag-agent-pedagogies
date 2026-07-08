# API — Agent Tuteur Sénégal

Base URL par défaut : `http://localhost:8000`. Toutes les routes (sauf
`/health`) lisent le tenant depuis l'en-tête `X-Tenant-Id` (défaut `default`).
Authentification JWT complète différée (cf. `docs/adr/0006-tenant-id-des-le-depart.md`).

## POST /api/chat

Question élève → réponse **streamée en SSE**. Exécute les nœuds a→e
(retrieve/frustration/hint/tool/guardrail) de façon synchrone puis streame la
génération LLM token par token.

**Requête**

```json
{
  "question": "comment dériver un quotient de fonctions ?",
  "student_id": "eleve1",
  "conversation_id": null,
  "curriculum_context": {"serie": "S1", "discipline": "Mathématiques"}
}
```

**Réponse** — `text/event-stream`, dans l'ordre :

```
data: {"meta": {"hint_level": 1, "hint_label": "Rappel de notion", "sources": [{"id": "...", "label": "...", "type_chunk": "exercice", "score": 0.03}], "scores": [0.03, ...], "tool_used": null, "frustration_score": 0.0}}

data: {"token": "Voici "}
data: {"token": "comment "}
...

data: {"done": {"message_id": "e287273a-...", "conversation_id": "02db4a08-..."}}
```

En cas d'échec de génération après le début du flux : `data: {"error": "..."}`
puis fin du flux (le status HTTP reste 200, déjà envoyé avec le premier octet).

**Codes d'erreur**
- `400` — anti-injection déclenché (`sanitize` détecte une tentative de
  détournement d'instructions) : **avant** tout appel LLM, aucun flux ouvert.
- `422` — payload invalide (Pydantic).
- `429` — rate limit dépassé (défaut 20/minute par IP).

## POST /api/upload → voir POST /api/documents

## POST /api/documents

Upload multi-fichiers (PDF/DOCX/TXT/MD) + métadonnées curriculaires
(formulaire). Indexation asynchrone (file ARQ, ou repli en tâche de fond du
même processus si Redis est indisponible).

**Requête** — `multipart/form-data` :
- `files` (un ou plusieurs fichiers)
- `niveau`, `classe`, `serie`, `discipline`, `chapitre`, `competence`,
  `examen_associe` (tous optionnels)

**Réponse** — `200`

```json
[{"document_id": "1ef35a0e-...", "filename": "cours.md", "status": "pending"}]
```

**Erreurs** : `400` extension non supportée, `413` fichier trop volumineux
(> `MAX_FILE_SIZE_MB`), `429` rate limit (10/minute).

## GET /api/documents

Liste les documents du tenant courant.

```json
[{"id": "...", "filename": "cours.md", "doc_type": "markdown", "status": "indexed", "error": null, "metadata": {"niveau": "secondaire"}, "created_at": "2026-07-08T09:33:42Z"}]
```

## GET /api/documents/{document_id}

Détail d'un document. `404` si absent ou tenant différent.

## GET /api/documents/{document_id}/status

SSE — sondage de la base toutes les 500 ms jusqu'à un état terminal :

```
data: {"status": "pending", "error": null}
data: {"status": "indexed", "error": null}
```

## DELETE /api/documents/{document_id}

Supprime le document (métadonnées Postgres) **et** ses chunks du vectorstore.
`404` si absent.

## POST /api/documents/{document_id}/reindex

Ré-indexe un document à partir d'un **nouveau fichier fourni** (`multipart`,
champ `file`) — la stack ne conserve pas le fichier original (pas de stockage
d'objets dans le périmètre verrouillé), donc la ré-indexation « à partir de la
source » exige de le refournir. Remplace les anciens chunks (`Indexer.reindex_source`).

## POST /api/search

Recherche hybride filtrée (sans passer par l'agent — utile pour explorer le
corpus indépendamment du tuteur).

**Requête**

```json
{"query": "comment dériver un quotient de fonctions", "curriculum_context": {"serie": "S1"}, "top_k": 5}
```

**Réponse**

```json
[{"id": "maths-ts1-derivees-md::000", "text": "...", "score": 0.0328, "dense_score": 0.41, "sparse_score": 2.88, "metadata": {"serie": "S1", "serie_alias": ["S1"], "type_chunk": "competence_complete", ...}}]
```

## GET /api/progression/{student_id}

Historique de progression + difficultés récurrentes (compétences où le niveau
d'indice a atteint ≥ 3 plusieurs fois).

```json
{
  "student_id": "eleve1",
  "history": [{"id": "...", "competence": "Dérivées", "hint_level": 1, "question": "...", "created_at": "..."}],
  "recurrent_difficulties": ["Dérivées"]
}
```

## POST /api/messages/{message_id}/feedback

Vote ±1 sur une réponse de l'agent.

**Requête** : `{"value": 1}` (ou `-1`). `422` si la valeur n'est pas dans
`{-1, 1}`. `404` si le message n'existe pas (ou tenant différent).

## GET /health

```json
{"status": "ok", "db": true, "redis": "not_configured", "qdrant": "not_configured", "llm": ["mistral", "ollama", "mock"]}
```

- `db` : `true`/`false` (ping SQL réel).
- `redis` : `"not_configured"` (le health check ne sonde pas le pool ARQ —
  l'absence de Redis est un mode dégradé assumé, pas une panne).
- `qdrant` : `"not_configured"` si `VECTOR_BACKEND=memory` ; `"ok"`/`"unreachable"` sinon.
- `llm` : chaîne de fallback effective (ex. `["mistral", "ollama", "mock"]`).
