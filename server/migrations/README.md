# Migrations

This directory will hold Alembic migration scripts managed by [Flask-Migrate](https://flask-migrate.readthedocs.io/).

## First-time setup

```bash
cd server
source .venv/bin/activate
export FLASK_APP=app
export FLASK_ENV=development

# 1. Ensure PostgreSQL is running (see ../docker-compose.yml)
docker compose up -d postgres

# 2. Initialize Alembic (only once — creates alembic.ini + env.py in this dir)
flask db init

# 3. Generate the baseline migration covering all current models
flask db migrate -m "baseline: schools, users, persons, devices, access_logs, snapshots, audit_logs"

# 4. Apply it
flask db upgrade
```

After step 2 is done, commit everything under `migrations/` to git — new
collaborators skip `flask db init` and go straight to `flask db upgrade`.

## Everyday commands

```bash
flask db migrate -m "add column X to persons"   # autogenerate
flask db upgrade                                # apply latest
flask db downgrade -1                           # roll back one revision
flask db history                                # list all revisions
flask db current                                # show DB's current revision
```

## Dev helper: blow away and recreate from code

When developing locally and you don't care about migrations yet, you can skip
Alembic and just create the full schema from the models:

```bash
flask dev-reset-db   # (command added in T1.8 — drops & recreates all tables)
```

**Never** run `dev-reset-db` on staging/production.