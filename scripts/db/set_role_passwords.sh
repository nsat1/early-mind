#!/usr/bin/env bash
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -v app_password="$DB_PASSWORD" \
    -v migration_password="$DB_MIGRATION_PASSWORD" <<'SQL'
ALTER ROLE early_mind_app PASSWORD :'app_password';
ALTER ROLE early_mind_migrator PASSWORD :'migration_password';
SQL
