# krystian-backend

FastAPI service powering Krystian's portfolio platform. See `CLAUDE.md` and `../docs/`.

## Run
- Full stack (recommended): from `../krystian-infra`, run `make up`.
- Standalone: `cp .env.example .env && uv run fastapi dev app/main.py` (needs Postgres + Redis).

API docs: http://localhost:8000/docs · Health: http://localhost:8000/v1/health

## Checks
```
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy app
```
