#!/bin/sh
# Applies real Alembic migrations before starting the server - replaces
# relying on app/main.py's `Base.metadata.create_all` dev/demo convenience
# for any deployed environment. Fails loudly (set -e) rather than starting
# uvicorn against an un-migrated schema.
set -e

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
