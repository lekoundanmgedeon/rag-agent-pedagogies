# agent-tuteur-web-next

Frontend **Next.js 16 / React 19 / TypeScript** de l'Agent Tuteur Sénégal —
espaces élève et administration.

Issu de la fusion NURU × ATS (phase P5) : design system repris du frontend
NURU, couche données entièrement réécrite, acquis du frontend Vue portés
(JWT, garde de route, streaming SSE). Voir
[ADR 0010](../docs/adr/0010-fusion-nuru-ats.md) et
[`JOURNAL_FUSION.md`](../JOURNAL_FUSION.md) module 8.

## Démarrer

```bash
npm install
npm run gen:api                       # types TS depuis le schéma OpenAPI
API_ORIGIN=http://localhost:8000 npm run dev
```

L'API doit tourner à côté (`make api` à la racine du dépôt).

## Le contrat d'API est généré, pas écrit

```bash
# 1. côté API — régénérer le schéma après toute modification de route
cd ../agent-tuteur-api && python scripts/export_openapi.py openapi.json

# 2. côté frontend — régénérer les types
npm run gen:api
```

`src/types/api.d.ts` **ne se modifie jamais à la main**. C'est le mécanisme qui
empêche les deux moitiés du projet de re-diverger : renommer un champ côté API
casse la compilation ici, au lieu de produire un `undefined` silencieux une fois
en production.

## Trois règles à ne pas enfreindre

1. **Aucune donnée inventée.** Une requête qui échoue lève une `ApiError` ;
   on affiche un état d'erreur. Le frontend NURU renvoyait des statistiques
   fabriquées quand l'API ne répondait pas — une panne devenait indétectable.
2. **La garde de route (`src/proxy.ts`) ne protège rien.** Elle évite d'afficher
   un écran vide. La seule autorité est l'API. Ne jamais y placer une décision
   de sécurité.
3. **La bonne réponse d'un quiz ne transite pas en clair.** Elle voyage scellée
   dans `quiz_token`, que l'on retransmet sans chercher à le lire.

## ⚠️ `API_ORIGIN` est lu au *build*, pas au démarrage

Next fige les redirections de `next.config.ts` dans le manifeste de
construction. Concrètement :

```bash
npm run build                          # ✗ pointera vers localhost:8000
API_ORIGIN=https://api.exemple.sn npm run build   # ✓
```

Ce piège a été rencontré pendant la mise au point : le frontend renvoyait
« Internal Server Error » sur `/health` alors que l'API répondait très bien.

En production, la redirection peut aussi être assurée par nginx (comme
aujourd'hui pour le frontend Vue) — c'est même préférable.

## Écrans

| Route | Rôle | Contenu |
|---|---|---|
| `/login` | public | Connexion |
| `/` | élève | Tuteur — chat streamé, rendu KaTeX |
| `/quiz` | élève | Générer un quiz, répondre, correction et badges |
| `/progression` | élève | Maîtrise par compétence, historique, badges |
| `/admin` | admin | Tableau de bord — état réel des services |
| `/admin/documents` | admin | Corpus : téléversement, état d'ingestion |
| `/admin/utilisateurs` | admin | Comptes et rôles |
| `/admin/recherche` | admin | Diagnostic de la recherche RAG |
| `/admin/journaux` | admin | Traces d'orchestration |

Les écrans **enseignant** et **parent** ne sont pas ici : leur modèle de données
existe (table `student_links`), mais les routes d'API correspondantes sont
reportées en v1.1 — décision de cadrage de la fusion.

## Vérifier

```bash
npm run typecheck   # tsc --noEmit
npm run build
```

Les deux sont exécutés par l'intégration continue.
