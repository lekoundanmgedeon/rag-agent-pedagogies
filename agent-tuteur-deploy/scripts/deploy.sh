#!/usr/bin/env bash
# Déploie (ou met à jour) la stack de production. Exécute les migrations
# avant de démarrer l'API/le worker (dépendance déclarée dans le compose,
# mais on échoue vite et lisiblement ici si .env.prod est incomplet).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env.prod ]; then
    echo "Erreur : .env.prod introuvable. Lance d'abord ./scripts/setup.sh" >&2
    exit 1
fi

echo "Construction des images..."
docker compose -f docker-compose.prod.yml --env-file .env.prod build

echo "Migrations..."
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm migrate

echo "Démarrage de la stack..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

echo "Stack démarrée. Statut :"
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
