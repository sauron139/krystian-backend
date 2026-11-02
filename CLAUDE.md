# krystian-backend

FastAPI service that powers the platform: content API for the public site, authenticated
admin API, contact-form handling, media uploads, and background jobs.
System context: `../CLAUDE.md` and `../docs/` (especially `ARCHITECTURE.md` and `API.md`).

## Stack
Python 3.13 · uv · FastAPI · Pydantic v2 · SQLAlchemy 2.0 async + asyncpg · Alembic ·
PostgreSQL · Redis · arq · S3 (R2 in prod; local stand-in TBD) · Ruff · mypy · pytest

## Planned structure
```
app/
├── main.py              # app factory, middleware, router registration
├── core/                # config (pydantic-settings), security, logging, errors
├── db/                  # engine, session, base model
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic request/response schemas
├── repositories/        # DB queries only
├── services/            # business logic (cache invalidation, email, storage)
├── api/
│   └── v1/
│       ├── public/      # read-only routes + POST /contact
│       └── admin/       # authenticated CRUD routes
├── workers/             # arq tasks (send email, image processing)
└── seed/                # placeholder seed data
migrations/              # Alembic
tests/
Dockerfile
pyproject.toml
.env.example
```

## Rules
- Routers are thin: validate input, call a service, return a schema.
- Every admin write invalidates the related Redis cache keys (in the service layer).
- Every schema change ships with an Alembic migration.
- Public endpoints never return drafts.
- Update `../docs/API.md` when the contract changes.

## Commands (planned)
- `uv run fastapi dev app/main.py` — run locally
- `uv run alembic upgrade head` — migrate
- `uv run python -m app.seed` — load placeholder content
- `uv run pytest` · `uv run ruff check --fix` · `uv run mypy app`
