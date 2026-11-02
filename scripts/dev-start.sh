#!/bin/sh
# Dev container entrypoint: bring the database up to date, then start with hot reload.
set -e
alembic upgrade head
python -m app.cli seed
python -m app.cli ensure-dev-admin
exec fastapi dev app/main.py --host 0.0.0.0 --port 8000
