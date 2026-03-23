#!/bin/sh
set -eu

set +e
python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, inspect, text

database_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
engine = create_engine(database_url)

core_tables = {"datasources", "saved_sqls", "export_tasks", "ai_configs"}

with engine.connect() as connection:
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())

    version_table_exists = "alembic_version" in existing_tables
    version_value = None
    if version_table_exists:
        try:
            version_value = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        except Exception:
            version_value = None

missing_core_tables = sorted(core_tables - existing_tables)
existing_core_tables = sorted(core_tables & existing_tables)

if version_value:
    print("[queryexport] alembic version detected:", version_value)
    sys.exit(0)

if not existing_core_tables:
    print("[queryexport] no application tables found, running migrations from scratch")
    sys.exit(0)

if not missing_core_tables:
    print("[queryexport] existing schema detected without alembic version, stamping head")
    sys.exit(10)

print("[queryexport] detected partially initialized schema without alembic version")
print("[queryexport] existing tables:", ", ".join(existing_core_tables))
print("[queryexport] missing tables:", ", ".join(missing_core_tables))
sys.exit(20)
PY
status=$?
set -e

echo "[queryexport] running database migrations..."
if [ "$status" -eq 10 ]; then
  alembic stamp head
fi

if [ "$status" -eq 20 ]; then
  echo "[queryexport] refusing to auto-migrate a partially initialized schema"
  exit 1
fi

alembic upgrade head

echo "[queryexport] starting backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
