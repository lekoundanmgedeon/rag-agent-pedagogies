# Agent Tuteur Sénégal — Frontend web (Vue 3)

Interface moderne remplaçant le frontend Streamlit. Deux espaces :

- **Espace élève** (`/`) — chat streaming (indices socratiques **ou** cours
  didactique selon l'intention), historique de conversations, sources RAG,
  feedback 👍/👎, page de progression, contexte curriculaire.
- **Espace administration** (`/admin`, rôle `admin`) — gestion des documents
  (upload multi-fichiers + métadonnées, statut d'indexation en temps réel,
  ré-indexation, suppression, vérification de cohérence), recherche RAG de
  débogage, logs d'orchestration, gestion des comptes, tableau de bord santé.

Thème **clair/sombre** avec bascule (défaut clair, suit le système si non défini).

## Stack

Vue 3 · Vite · Pinia · vue-router · axios · marked + DOMPurify. Aucune
dépendance UI lourde : le design system vit dans `src/App.vue` (variables CSS).

## Prérequis

L'API `agent-tuteur-api` doit tourner (défaut `http://localhost:8000`) avec
l'**authentification activée** (JWT). Crée au moins un compte admin :

```bash
# depuis agent-tuteur-api/
PYTHONPATH=src python scripts/create_user.py \
  --email admin@ecole.sn --password 'motdepasse' --role admin --tenant default
```

## Développement

```bash
npm install
npm run dev            # http://localhost:5173 (proxy /api et /health -> :8000)
```

Cible API surchargeable : `VITE_API_TARGET=http://autre-hote:8000 npm run dev`.

## Production

```bash
npm run build          # génère dist/
```

Servir `dist/` en statique derrière un reverse-proxy qui route `/api` et
`/health` vers l'API (voir `agent-tuteur-deploy/nginx/`).

## Contrat backend

Toutes les requêtes portent `Authorization: Bearer <jwt>` (obtenu via
`POST /api/auth/login`). Le streaming (`/api/chat`, statut d'ingestion) utilise
`fetch` — et non `EventSource` — pour pouvoir porter l'en-tête. Le service
unique `src/services/api.js` centralise tous les appels ; aucune logique
pédagogique côté front.
