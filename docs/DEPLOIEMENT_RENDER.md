# Déploiement de démonstration sur Render (mono-conteneur)

> **⚠️ Ce document décrit le déploiement du frontend Vue — ce qui est toujours
> exact, mais provisoire.**
>
> Le frontend courant du projet est le **Next.js** (`agent-tuteur-web-next/`),
> prêt et vérifié de bout en bout. La bascule du déploiement attend un arbitrage
> d'équipe (point **V7**, cf. [`STATUS.md`](STATUS.md) §5), pour deux raisons :
> elle touche la production, et les deux frontends **diffèrent en nature** — le
> Vue est un build **statique** que FastAPI peut servir depuis `spa_dist_dir`,
> tandis que Next exige un **processus Node** qui tourne. Le mono-conteneur décrit
> ici ne transpose donc pas tel quel.
>
> Cinq fichiers seront à reprendre le jour de la bascule : `Dockerfile.render`,
> `render.yaml`, les deux `docker-compose` et le `Makefile`. En attendant, tout
> ce qui suit s'applique sans réserve.

*Complète [`GUIDE_LANCEMENT.md`](GUIDE_LANCEMENT.md), qui couvre les modes de
lancement locaux (A/B/C). Ce document décrit un quatrième mode : une **démo
publique** hébergée, volontairement réduite — ce n'est pas un déploiement de
production, pour lequel `agent-tuteur-deploy/docker-compose.prod.yml` reste la
référence.*

## 1. Pourquoi une image dédiée

Render (comme la plupart des PaaS) **ne lit pas `docker-compose.yml`** : chaque
service se déclare individuellement et se facture séparément. Porter la stack de
production telle quelle (postgres + redis + qdrant + api + worker + web + nginx)
donnerait sept services payants pour une démo.

`Dockerfile.render` (à la racine) construit donc une image unique qui regroupe le
SPA Vue et l'API FastAPI. Les `Dockerfile` de `agent-tuteur-api/` et
`agent-tuteur-web/` restent inchangés et font toujours foi pour Docker Compose.

Trois avantages au mono-conteneur, au-delà du coût :

- **Un seul démarrage à froid.** Sur l'offre gratuite, un service s'endort après
  15 minutes d'inactivité ; deux services = deux réveils à enchaîner.
- **Pas de CORS.** SPA et API partagent la même origine.
- **SSE intact.** Le flux `/api/chat` n'est relayé par aucun proxy
  intermédiaire susceptible de le bufferiser — c'est le point qui casse le plus
  souvent les démos hébergées.

## 2. Ce qui est retiré, et pourquoi c'est sans danger

| Service de la prod | Sort en démo | Justification |
|---|---|---|
| Worker ARQ + Redis | **Retirés** | `api/main.py::_try_create_arq_pool` renvoie `None` si Redis est injoignable, sans bloquer le démarrage ; `api/routes/documents.py::_schedule_ingestion` bascule alors sur les `BackgroundTasks` du process API. L'ingestion reste fonctionnelle, simplement in-process. Un Background Worker Render est de toute façon payant. |
| Qdrant | **Retiré** (`VECTOR_BACKEND=memory`) | Le `lifespan` de `api/main.py` ré-ingère le corpus d'exemple à chaque démarrage quand le store mémoire est vide. Pas de service vectoriel à héberger. |
| nginx | **Retiré** | L'API sert elle-même le SPA (`api/main.py::_mount_spa`). |
| PostgreSQL | **Remplacé** par la base managée Render | Voir §4 pour les deux adaptations nécessaires. |

**Contrepartie du `VECTOR_BACKEND=memory`** : les documents téléversés depuis
l'espace admin disparaissent à chaque redémarrage (seul le corpus d'exemple
revient). Pour les conserver, voir §6.

## 3. Déployer

1. Pousser la branche sur GitHub / GitLab.
2. Render → **New** → **Blueprint**, pointer sur le dépôt. `render.yaml` (racine)
   décrit le service web et la base.
3. Saisir les variables marquées `sync: false` dans le tableau de bord — elles
   ne sont jamais commitées :
   - `MISTRAL_API_KEY` — sans elle, `LLM_BACKEND=auto` retombe sur le backend
     **mock** (réponses factices : la démo tourne, mais ne démontre rien).
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD` — compte administrateur initial. Sans lui,
     personne ne peut se connecter : aucun compte n'est câblé en dur.

`JWT_SECRET` est généré aléatoirement par Render (`generateValue: true`).

Au premier démarrage, `agent-tuteur-deploy/render-start.sh` enchaîne migrations
Alembic → création du compte admin → uvicorn. Les deux premières étapes sont
idempotentes : les redéploiements suivants les traversent sans effet.

## 4. Les deux pièges de la base managée

`render-start.sh` les traite automatiquement, mais il faut les connaître pour
déboguer :

- **Dialecte.** Render fournit une URL `postgresql://`, destinée au driver
  synchrone psycopg. L'application est 100 % async et attend
  `postgresql+asyncpg://`. Le script réécrit le préfixe.
- **TLS.** asyncpg ne connaît pas le paramètre libpq `sslmode` ; son équivalent
  est `ssl`, aux mêmes valeurs. Le script renomme le paramètre. Cela ne concerne
  que l'URL *externe* — `render.yaml` utilise l'URL **interne** (même région,
  sans TLS), plus rapide et sans ce paramètre.

**RLS** ne demande en revanche aucune adaptation : la migration
`0002_enable_rls` déclare `FORCE ROW LEVEL SECURITY`, donc les policies
s'appliquent même au rôle propriétaire des tables. L'astuce du rôle applicatif
séparé (`agent-tuteur-deploy/postgres-init/01-app-role.sh`) ne sert que face à
un *superuser* Postgres, qui contourne RLS quoi qu'il arrive — le rôle fourni
par Render n'en est pas un. Rien à rejouer.

## 5. Limites à assumer

- **Mise en veille après 15 min d'inactivité** : le premier accès prend ~50 s.
  Sur un flux SSE, le tout premier message après réveil peut sembler figé.
- **La base PostgreSQL gratuite expire au bout de 30 jours** (politique Render).
- **Ollama est injoignable** depuis Render : la chaîne de repli LLM se réduit à
  Mistral → mock.
- **512 Mo de RAM.** Mesuré à ~170 Mo au repos, corpus d'exemple indexé :
  confortable. C'est `EMBEDDING_BACKEND=light` (pur numpy, aucun modèle
  téléchargé) qui rend cette marge possible — `bge_m3` ne tiendrait pas.

## 6. Conserver les documents téléversés

Créer un cluster gratuit sur **Qdrant Cloud** (1 Go), puis dans `render.yaml` :
passer `VECTOR_BACKEND` à `qdrant` et décommenter `QDRANT_URL` / `QDRANT_API_KEY`
(à saisir dans le tableau de bord). Aucun changement de code — le backend Qdrant
est déjà celui de la production.

Au premier démarrage après la bascule, les documents déjà marqués `indexed` en
base n'auront pas de vecteurs dans le nouveau store : la vérification de
cohérence du `lifespan` les signalera comme `orphaned`. C'est le comportement
attendu ; les réindexer depuis l'espace admin.

## 7. Tester l'image en local

Le contexte de build est la **racine** du dépôt (les deux sous-projets sont
nécessaires) :

```bash
docker build -f Dockerfile.render -t agent-tuteur-demo .

docker network create render-sim
docker run -d --name render-pg --network render-sim \
    -e POSTGRES_USER=tuteur -e POSTGRES_PASSWORD=tuteur -e POSTGRES_DB=tuteur \
    postgres:16-alpine

docker run --rm --network render-sim -p 10000:10000 \
    -e PORT=10000 \
    -e DATABASE_URL="postgresql://tuteur:tuteur@render-pg:5432/tuteur" \
    -e VECTOR_BACKEND=memory -e EMBEDDING_BACKEND=light -e LLM_BACKEND=auto \
    -e JWT_SECRET=dev-secret \
    -e ADMIN_EMAIL=admin@demo.sn -e ADMIN_PASSWORD=demo12345 \
    agent-tuteur-demo
```

UI sur <http://localhost:10000>. `REDIS_URL` est volontairement omis : sa valeur
par défaut (`localhost:6379`) est injoignable dans le conteneur, ce qui exerce
précisément le mode dégradé de la démo.

> Pour reproduire fidèlement les privilèges de Render, créer un rôle
> `NOSUPERUSER NOBYPASSRLS` propriétaire de la base plutôt que d'utiliser le
> superuser du conteneur `postgres` — sinon RLS est contourné et l'isolation
> multi-tenant n'est pas réellement testée.
