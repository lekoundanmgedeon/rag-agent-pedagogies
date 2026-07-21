# Déploiement d'un test en ligne (VPS unique)

Procédure pour mettre la stack complète en ligne sur **un seul VPS**, avec une
URL HTTPS à envoyer à l'équipe. Complète [`GUIDE_LANCEMENT.md`](GUIDE_LANCEMENT.md)
(lancement local) avec le « comment » du déploiement distant.

**Configuration retenue** : VPS + `docker-compose.prod.yml`, URL publique sans
authentification, corpus = les 12 leçons de `lessons/`.

> ⚠️ **Lire la section [9. Ce que « sans authentification » implique](#9-ce-que--sans-authentification--implique) avant d'envoyer le lien.**
> L'API n'a aucun contrôle d'accès : toute personne ayant l'URL peut supprimer
> le corpus et lire toutes les conversations.

---

## Table des matières

1. [Ce qui tourne, et pourquoi un VPS](#1-ce-qui-tourne-et-pourquoi-un-vps)
2. [Prérequis](#2-prérequis)
3. [Provisionner le VPS](#3-provisionner-le-vps)
4. [Récupérer le code](#4-récupérer-le-code)
5. [Certificat TLS](#5-certificat-tls)
6. [Configurer `.env.prod`](#6-configurer-envprod)
7. [Déployer](#7-déployer)
8. [Ingérer les 12 leçons](#8-ingérer-les-12-leçons)
9. [Ce que « sans authentification » implique](#9-ce-que--sans-authentification--implique)
10. [Vérification avant envoi à l'équipe](#10-vérification-avant-envoi-à-léquipe)
11. [Exploitation courante](#11-exploitation-courante)
12. [Dépannage](#12-dépannage)

---

## 1. Ce qui tourne, et pourquoi un VPS

Le frontend Streamlit est un **client HTTP pur** (`services/api_client.py`) : il
ne contient aucune logique métier et ne sait rien de la base ni du vectorstore.
Le déployer seul (Streamlit Community Cloud) ne déploie donc quasiment rien —
il faudrait de toute façon héberger l'API, PostgreSQL et Qdrant ailleurs.

`docker-compose.prod.yml` lance les 7 services sur une seule machine :

| Service | Rôle | Exposé sur l'hôte |
|---|---|---|
| `nginx` | Reverse proxy TLS, rate limiting | **80 / 443 (seul)** |
| `frontend` | Streamlit (`API_BASE_URL=http://api:8000`, réseau interne) | non |
| `api` | FastAPI + SSE | non |
| `worker` | Ingestion asynchrone ARQ | non |
| `postgres` | Persistance + RLS multi-tenant | non |
| `redis` | File de l'ingestion | non |
| `qdrant` | Vecteurs (`VECTOR_BACKEND=qdrant`) | non |

`nginx.conf` gère déjà les deux besoins délicats : **WebSocket** pour Streamlit
(`proxy_set_header Upgrade`, `proxy_read_timeout 86400s`) et **SSE non
bufferisé** pour `/api/chat` et `/api/documents` (`proxy_buffering off`).

---

## 2. Prérequis

- Un VPS Ubuntu 22.04/24.04, **4 Go de RAM minimum** (Qdrant + Postgres + Redis
  + 2 processus Python + nginx). 2 vCPU suffisent.
  `EMBEDDING_BACKEND=light` étant déterministe et sans modèle à télécharger,
  aucun GPU ni RAM supplémentaire n'est requis — **ne pas** passer à `bge_m3`,
  `FlagEmbedding` est commenté dans `requirements.txt` et l'API ne démarrerait pas.
- Un **nom de domaine** pointant sur l'IP du VPS (enregistrement `A`).
  Un sous-domaine gratuit (DuckDNS, etc.) fait l'affaire. Sans domaine, il faut
  se rabattre sur un certificat auto-signé — voir [§5.2](#52-repli--certificat-auto-signé-sans-domaine).
- Une **clé API Mistral** valide (celle de `agent-tuteur-api/.env` en local).
- Le repo à jour sur `main` (le mode cours didactique et l'ancrage RAG des
  leçons sont dans les commits `8ffd48c` et `fe17960`).

Dans toute la suite, remplacer `tuteur.exemple.sn` par votre domaine réel.

---

## 3. Provisionner le VPS

```bash
ssh root@IP_DU_VPS

# Docker + compose plugin
apt update && apt install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  > /etc/apt/sources.list.d/docker.list
apt update && apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

docker --version && docker compose version
```

Pare-feu — **n'ouvrir que 80 et 443** (le compose n'expose déjà rien d'autre,
mais une règle explicite évite qu'un `docker run` ultérieur perce la machine) :

```bash
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
```

---

## 4. Récupérer le code

Le compose construit les images depuis `../agent-tuteur-api` et
`../agent-tuteur-frontend` : **tout le dépôt** doit être présent, pas seulement
`agent-tuteur-deploy/`.

```bash
cd /opt
git clone https://github.com/lekoundanmgedeon/rag-agent-pedagogies.git
cd rag-agent-pedagogies
git checkout main
```

> Le `remote` local est en SSH. Si le dépôt est **privé**, le clone HTTPS
> demandera des identifiants : créer une *deploy key* en lecture seule sur
> GitHub et cloner en SSH, ou utiliser un token personnel.

---

## 5. Certificat TLS

### 5.1 — Let's Encrypt (recommandé)

À faire **avant** de démarrer la stack : `certbot --standalone` a besoin du
port 80, que nginx occupera ensuite.

```bash
apt install -y certbot
certbot certonly --standalone -d tuteur.exemple.sn --agree-tos -m vous@exemple.sn -n
```

nginx lit les certificats depuis le bind mount `./nginx/certs`. **Copier les
fichiers, ne pas faire de lien symbolique** : les liens de
`/etc/letsencrypt/live/` pointent vers `../../archive/`, hors du volume monté,
et seraient irrésolus dans le conteneur.

```bash
cd /opt/rag-agent-pedagogies/agent-tuteur-deploy
mkdir -p nginx/certs
cp /etc/letsencrypt/live/tuteur.exemple.sn/fullchain.pem nginx/certs/fullchain.pem
cp /etc/letsencrypt/live/tuteur.exemple.sn/privkey.pem   nginx/certs/privkey.pem
```

Renouvellement (le certificat expire au bout de 90 jours) :

```bash
cat > /etc/cron.monthly/renew-tuteur-cert <<'EOF'
#!/bin/bash
set -e
certbot renew --quiet --pre-hook "docker stop agent-tuteur-senegal-nginx-1" \
              --post-hook "docker start agent-tuteur-senegal-nginx-1"
D=/opt/rag-agent-pedagogies/agent-tuteur-deploy/nginx/certs
cp /etc/letsencrypt/live/tuteur.exemple.sn/fullchain.pem $D/fullchain.pem
cp /etc/letsencrypt/live/tuteur.exemple.sn/privkey.pem   $D/privkey.pem
docker restart agent-tuteur-senegal-nginx-1
EOF
chmod +x /etc/cron.monthly/renew-tuteur-cert
```

### 5.2 — Repli : certificat auto-signé (sans domaine)

`scripts/setup.sh` en génère un automatiquement. **Conséquence** : chaque
membre de l'équipe verra un avertissement de sécurité à contourner à la main,
et certains navigateurs bloquent le WebSocket de Streamlit sur un certificat
non fiable — l'interface reste alors figée sur « Connecting… ». À éviter si
possible.

---

## 6. Configurer `.env.prod`

```bash
cd /opt/rag-agent-pedagogies/agent-tuteur-deploy
./scripts/setup.sh     # crée .env.prod (+ cert auto-signé si nginx/certs est vide)
```

Toutes les variables du compose sont déclarées `${VAR:?}` — **une valeur
manquante fait échouer le démarrage** plutôt que de retomber sur un secret de
dev. Éditer `.env.prod` :

```bash
POSTGRES_SUPERUSER=tuteur
POSTGRES_SUPERUSER_PASSWORD=<openssl rand -base64 24>
POSTGRES_APP_USER=tuteur_app
POSTGRES_APP_PASSWORD=<openssl rand -base64 24>
POSTGRES_DB=tuteur
REDIS_PASSWORD=<openssl rand -base64 24>
QDRANT_API_KEY=<openssl rand -base64 24>
MISTRAL_API_KEY=<votre clé Mistral>
MISTRAL_MODEL=mistral-small-latest
CORS_ORIGINS=https://tuteur.exemple.sn
JWT_SECRET=<openssl rand -base64 32>
DEFAULT_TENANT=default
EMBEDDING_BACKEND=light
```

Générer les secrets d'un coup :

```bash
for v in POSTGRES_SUPERUSER_PASSWORD POSTGRES_APP_PASSWORD REDIS_PASSWORD QDRANT_API_KEY JWT_SECRET; do
    echo "$v=$(openssl rand -base64 24 | tr -d '/+=')"
done
```

Points d'attention :

- **`POSTGRES_APP_USER` ≠ `POSTGRES_SUPERUSER`.** `postgres-init/01-app-role.sh`
  crée le rôle applicatif en `NOSUPERUSER NOBYPASSRLS` : c'est la condition pour
  que le Row Level Security s'applique réellement. Un superuser contourne
  *toujours* RLS, même avec `FORCE ROW LEVEL SECURITY`.
- Ce script d'init ne s'exécute **qu'à la création du volume Postgres**. Si vous
  changez `POSTGRES_APP_USER` après un premier démarrage, il faut détruire le
  volume (`down -v`) ou créer le rôle à la main.
- `CORS_ORIGINS` : jamais `*`. Fonctionnellement peu critique ici (Streamlit
  appelle l'API côté serveur, pas depuis le navigateur), mais la variable est
  obligatoire et vaut pour tout futur client web.
- `.env.prod` est dans `.gitignore` — ne jamais le commiter.

---

## 7. Déployer

```bash
./scripts/deploy.sh
```

Le script enchaîne `build` → `run --rm migrate` (Alembic, avec le rôle
superuser propriétaire des tables) → `up -d`. Comptez 5 à 10 minutes au premier
build.

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
curl -s https://tuteur.exemple.sn/health | python3 -m json.tool
```

Attendu :

```json
{
  "status": "ok",
  "db": true,
  "redis": "ok",
  "qdrant": "ok",
  "llm": ["mistral", "mock"],
  "documents_orphaned": 0
}
```

- `"llm"` **doit** contenir `mistral` en tête. S'il n'y a que `["mock"]`, la clé
  Mistral n'est pas prise en compte : l'agent répondra avec des réponses
  factices — inutilisable pour un test d'équipe.
- `"redis": "degraded"` n'est pas bloquant (l'ingestion se replie sur
  `BackgroundTasks` dans le processus API), mais signale que le worker ne
  consomme rien.
- `"qdrant": "unreachable"` est bloquant : l'API ne sert aucun contexte RAG.

---

## 8. Ingérer les 12 leçons

Le volume Qdrant est vide au premier démarrage. L'auto-ingestion du corpus de
démo au `lifespan` **ne s'applique qu'au backend `memory`** — en production
(`VECTOR_BACKEND=qdrant`), rien n'est chargé automatiquement.

Un script est fourni :

```bash
cd /opt/rag-agent-pedagogies/agent-tuteur-deploy
./scripts/seed-lessons.sh https://tuteur.exemple.sn default
# certificat auto-signé : ajouter --insecure en 3ᵉ argument
```

Il envoie les 12 fichiers en **un seul appel multipart** puis sonde
`/api/documents` jusqu'à ce qu'aucun document ne soit `pending`.

**Aucune métadonnée de formulaire n'est envoyée, volontairement.** Chaque leçon
porte son frontmatter YAML (`serie: S2`, `serie_alias: [S2, S4]`, `chapitre`,
`discipline`…), fusionné automatiquement par `ingestion/pipeline.py`. Saisir une
série à la main risquerait d'écrire une valeur hors taxonomie (`"S"` au lieu de
`S2`), ce qui fait échouer le filtrage RAG **en silence** — piège n°4 de
`docs/STATUS.md`.

Résultat attendu :

```
✅ Corpus prêt : 12 leçon(s) indexée(s).
```

Vérifier que le RAG retourne bien du contenu :

```bash
curl -s -X POST https://tuteur.exemple.sn/api/search \
  -H "Content-Type: application/json" -H "X-Tenant-Id: default" \
  -d '{"query":"forme trigonométrique d un nombre complexe","top_k":3}' \
  | python3 -m json.tool
```

---

## 9. Ce que « sans authentification » implique

Il n'y a **aucun contrôle d'accès** dans l'application. `api/dependencies.py`
lit simplement l'en-tête `X-Tenant-Id` (défaut : `default`) — c'est un
séparateur de données, pas une authentification : n'importe qui peut envoyer
l'en-tête de son choix.

Toute personne disposant de l'URL peut donc :

- discuter avec le tuteur (consomme votre quota Mistral) ;
- **uploader et supprimer des documents** (page Upload → `DELETE /api/documents/{id}`) ;
- **lire toutes les conversations de tous les élèves** (page Logs → `GET /api/logs/chat`).

Ce qui vous protège malgré tout :

- L'URL n'est pas indexée tant que vous ne la publiez pas.
- Double rate limiting : nginx (20 req/min sur `/api/chat`, 120 sur le reste,
  par IP) + slowapi côté API.
- Les garde-fous anti-injection de l'agent (`agent/guardrails.py`).

⚠️ **Le rate limit nginx est par adresse IP.** Si votre équipe teste depuis le
même bureau (une seule IP publique NAT), les 20 req/min de `chat_zone` sont
partagées entre tous et vous verrez des HTTP 429. Pour une session de test
collective, augmenter `rate=20r/m` dans `nginx/nginx.conf` et
`RATE_LIMIT_CHAT` côté API.

**Recommandations minimales** : n'envoyez le lien qu'en message privé, prévenez
l'équipe que la page Upload est destructive, et faites une sauvegarde avant
l'envoi (voir §11). Si vous changez d'avis, un `auth_basic` dans nginx est la
protection la moins invasive — dites-le-moi, c'est ~10 lignes.

---

## 10. Vérification avant envoi à l'équipe

Cette check-list couvre les points qui **ne peuvent pas** être validés par les
tests unitaires ni depuis le shell :

```bash
curl -s https://tuteur.exemple.sn/health          # llm contient "mistral", qdrant "ok"
curl -s https://tuteur.exemple.sn/api/documents -H "X-Tenant-Id: default" | grep -c indexed
docker compose -f docker-compose.prod.yml --env-file .env.prod ps   # 6 up + migrate exited(0)
```

Puis **dans un navigateur**, sur `https://tuteur.exemple.sn` :

- [ ] Le cadenas TLS est valide (pas d'avertissement).
- [ ] La sidebar affiche `🟢 API ok — LLM: mistral → mock`. Un `🔴 API
      injoignable` signale un problème de résolution `api:8000` côté frontend.
- [ ] **Poser une question d'exercice** (« je bloque sur le calcul de
      $\int_0^1 xe^x dx$ ») : la réponse doit **streamer token par token**. Si
      elle apparaît d'un bloc après un long silence, nginx bufferise le SSE.
- [ ] Relancer avec « un autre indice ? » : la réponse doit rester sur le même
      exercice. C'est le correctif d'historique de conversation (`fe17960`) —
      s'il régresse, le sujet part à la dérive.
- [ ] **Poser une question de cours** (« explique-moi les nombres complexes ») :
      le bandeau doit afficher `📚 Cours — Section 1/N` et non « Niveau
      d'indice ». C'est le mode didactique du commit `8ffd48c`.
- [ ] Les sources RAG citées pointent bien vers les leçons ingérées.
- [ ] Sidebar : créer une 2ᵉ conversation, recharger la page (F5), vérifier que
      les deux sessions sont listées et reprenables. **Le rendu Streamlit de
      cette sidebar n'a jamais été validé en navigateur** (cf. `docs/STATUS.md`)
      — c'est le point le plus incertain de la check-list.
- [ ] Page Upload : déposer un `.md` de test. Streamlit derrière un reverse
      proxy peut échouer sur `st.file_uploader` (protection XSRF) — à confirmer
      en conditions réelles. Supprimer le document de test ensuite.
- [ ] Page Progression et page Logs s'affichent sans erreur.

---

## 11. Exploitation courante

```bash
cd /opt/rag-agent-pedagogies/agent-tuteur-deploy
C="docker compose -f docker-compose.prod.yml --env-file .env.prod"

$C logs -f api            # logs JSON structurés (observability.py)
$C logs -f frontend worker
$C ps
$C restart api
```

**Mettre à jour après un commit** :

```bash
git pull && ./scripts/deploy.sh
```

**Sauvegarder avant d'ouvrir aux tests** (`scripts/backup.sh` est fourni) :

```bash
./scripts/backup.sh
```

**Repartir d'un corpus propre** (efface *toutes* les données, y compris les
conversations) :

```bash
$C down -v && ./scripts/deploy.sh && ./scripts/seed-lessons.sh https://tuteur.exemple.sn
```

**Arrêter le test** :

```bash
$C down          # conserve les volumes
$C down -v       # supprime aussi les données
```

---

## 12. Dépannage

| Symptôme | Cause | Correction |
|---|---|---|
| `POSTGRES_APP_USER requis` au démarrage | Variable absente de `.env.prod` | Toutes les variables du §6 sont obligatoires (`${VAR:?}`) |
| `/health` → `"llm": ["mock"]` | `MISTRAL_API_KEY` vide ou invalide | Corriger `.env.prod`, puis `$C up -d --force-recreate api` |
| `/health` → `"qdrant": "unreachable"` | Qdrant KO ou `QDRANT_API_KEY` désaccordée entre `api`/`worker`/`qdrant` | `$C logs qdrant` ; la même valeur doit être lue par les 3 services |
| `InsufficientPrivilegeError` sur les requêtes | `POSTGRES_APP_USER` créé superuser, ou volume préexistant sans le rôle | `down -v` puis redéployer (le script d'init ne tourne qu'à la création du volume) |
| Streamlit figé sur « Connecting… » | WebSocket bloqué (certificat auto-signé, ou proxy tiers devant nginx) | Utiliser un vrai certificat (§5.1) |
| Réponse du chat affichée d'un bloc, sans streaming | Buffering SSE | `nginx.conf` a `proxy_buffering off` sur `/api/chat` : vérifier qu'aucun CDN/proxy (ex. Cloudflare en mode proxy) ne se place devant |
| HTTP 429 pendant une démo collective | Rate limit par IP partagée par tout le bureau | Augmenter `chat_zone` dans `nginx.conf` et `RATE_LIMIT_CHAT` |
| Documents `orphaned` dans `/health` | Vecteurs disparus du store (volume Qdrant recréé) | `POST /api/documents/verify-all` puis ré-ingérer (§8) |
| L'agent répond hors-sujet après plusieurs tours | Régression du rappel d'historique | Voir `docs/STATUS.md` : `chat.py` doit passer `conversation_history` à `TutorAgent.prepare` |
| Le mode cours ne se déclenche pas | Leçons non ingérées, ou frontmatter écrasé | Vérifier que `metadata.chapitre` est renseigné dans `GET /api/documents` |
| Build OOM / VPS qui rame | Moins de 4 Go de RAM | Ajouter du swap, ou construire les images ailleurs et les pousser |
