#!/usr/bin/env bash
# Point d'entrée de l'image mono-conteneur (Dockerfile.render).
#
# Remplace à lui seul les services `migrate`, `createadmin` et `api` de
# docker-compose : sur un PaaS type Render, il n'y a qu'un conteneur, et les
# migrations doivent tourner avant que le serveur n'accepte du trafic.
set -euo pipefail

# --- 1. Normalisation de DATABASE_URL -----------------------------------------
# Les bases managées (Render, Heroku, Neon…) fournissent une URL `postgresql://`
# destinée au driver synchrone psycopg. L'application est 100 % async : elle
# attend le dialecte `postgresql+asyncpg`. Et asyncpg ne connaît pas le paramètre
# `sslmode` (option libpq) — son équivalent est `ssl`, aux mêmes valeurs.
if [[ -n "${DATABASE_URL:-}" ]]; then
    case "$DATABASE_URL" in
        postgres://*)   DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgres://}" ;;
        postgresql://*) DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}" ;;
    esac
    DATABASE_URL="${DATABASE_URL//\?sslmode=/\?ssl=}"
    DATABASE_URL="${DATABASE_URL//&sslmode=/&ssl=}"
    export DATABASE_URL
fi

# --- 2. Schéma de base --------------------------------------------------------
# Idempotent : sans effet si le schéma est déjà à jour. Bloquant volontairement —
# démarrer l'API sur un schéma obsolète produirait des erreurs à chaque requête.
echo "▶ Migrations Alembic…"
alembic upgrade head

# --- 3. Compte administrateur initial -----------------------------------------
# Sans lui, personne ne peut se connecter (aucun compte n'est câblé en dur).
# Idempotent (cf. scripts/create_user.py) ; non bloquant, pour qu'un échec ici
# n'empêche pas l'API de démarrer si le compte a déjà été créé autrement.
if [[ -n "${ADMIN_EMAIL:-}" && -n "${ADMIN_PASSWORD:-}" ]]; then
    echo "▶ Amorçage du compte admin ${ADMIN_EMAIL}…"
    python scripts/create_user.py \
        --email "$ADMIN_EMAIL" \
        --password "$ADMIN_PASSWORD" \
        --role admin \
        --tenant "${DEFAULT_TENANT:-default}" || echo "⚠️  Amorçage admin échoué — on continue."
else
    echo "ℹ️  ADMIN_EMAIL/ADMIN_PASSWORD absents : aucun compte amorcé."
fi

# --- 4. Serveur ---------------------------------------------------------------
# `exec` : uvicorn devient PID 1 et reçoit directement les signaux d'arrêt du
# PaaS (sans quoi les arrêts se feraient à coups de SIGKILL après timeout).
# $PORT est imposé par la plateforme (10000 chez Render).
echo "▶ Démarrage de l'API sur le port ${PORT:-8000}…"
exec uvicorn agent_tuteur.api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
