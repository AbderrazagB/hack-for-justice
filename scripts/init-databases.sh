#!/bin/sh
# Runs once, on an empty Postgres data directory.
#
# The application database is created by POSTGRES_DB; the test database is not,
# and pytest needs it. Creating it here means a fresh clone can run the suite
# without a manual psql step nobody remembers.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
  SELECT 'CREATE DATABASE ${POSTGRES_DB}_test'
  WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB}_test')\gexec
EOSQL
