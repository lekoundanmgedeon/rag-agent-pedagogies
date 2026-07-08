#!/usr/bin/env bash
# Sauvegarde PostgreSQL (pg_dump) + volume Qdrant, horodatées dans ./backups/.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env.prod ]; then
    echo "Erreur : .env.prod introuvable." >&2
    exit 1
fi
set -a; source .env.prod; set +a

STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p backups

echo "Sauvegarde PostgreSQL..."
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres \
    pg_dump -U "$POSTGRES_SUPERUSER" "$POSTGRES_DB" | gzip > "backups/postgres_${STAMP}.sql.gz"

echo "Sauvegarde du volume Qdrant..."
docker run --rm \
    -v agent-tuteur-senegal_qdrant_data:/data:ro \
    -v "$(pwd)/backups:/backup" \
    alpine tar czf "/backup/qdrant_${STAMP}.tar.gz" -C /data .

echo "Sauvegardes écrites dans ./backups/ :"
ls -lh backups/*"${STAMP}"*
