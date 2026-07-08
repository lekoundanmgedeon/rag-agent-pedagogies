#!/usr/bin/env bash
# Rôle applicatif NON-superuser : condition nécessaire pour que le Row Level
# Security (migration 0002_enable_rls) s'applique réellement — un superuser
# Postgres (POSTGRES_USER, celui de ce script d'init) contourne TOUJOURS RLS,
# même avec FORCE ROW LEVEL SECURITY.
#
# Script shell (pas .sql) pour pouvoir interpoler les identifiants depuis les
# variables d'environnement du conteneur (POSTGRES_APP_USER/PASSWORD, définies
# dans docker-compose.*.yml) — un .sql brut ne supporte pas cette substitution.
#
# Les migrations Alembic tournent avec le rôle superuser (propriétaire des
# tables, seul capable de CREATE TABLE / CREATE POLICY / ENABLE ROW LEVEL
# SECURITY) ; l'API et le worker se connectent avec ce rôle applicatif.
set -euo pipefail

APP_USER="${POSTGRES_APP_USER:-tuteur_app}"
APP_PASSWORD="${POSTGRES_APP_PASSWORD:-tuteur_app_password}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${APP_USER} LOGIN PASSWORD '${APP_PASSWORD}' NOSUPERUSER NOBYPASSRLS;

    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${APP_USER};
    GRANT USAGE ON SCHEMA public TO ${APP_USER};

    -- Les tables n'existent pas encore (créées ensuite par Alembic) : on
    -- déclare les privilèges par défaut pour les futures tables créées par
    -- le rôle superuser courant.
    ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_USER};

    ALTER DEFAULT PRIVILEGES FOR ROLE ${POSTGRES_USER} IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO ${APP_USER};
EOSQL
