# Contributing Guide

## Setup

```bash
docker compose up -d              # Start everything
# OR just the database:
docker compose up db -d
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

## Branches

```
feature/<module>-<desc>     e.g. feature/calibration-gaze-stream
fix/<module>-<desc>         e.g. fix/survey-publish-error
```

## Commits

```
<type>(<scope>): <desc>
Types:   feat | fix | docs | style | refactor | test | chore
Scopes:  auth | survey | post | tracking | export | frontend | ci
```

## PR Rules

- Under 400 lines of diff — split large features
- Fill out the PR template
- 1 approval required
- CI must pass
- Squash merge only

## Adding a New Endpoint

1. Add Pydantic schemas in `schemas/`
2. Add router function in `routers/` with docstring + type hints
3. If new table needed: add model in `models/`, register in `models/__init__.py`
4. Verify at http://localhost:8000/docs
5. Open PR

**You do NOT need to update a separate API doc file — FastAPI Swagger auto-generates from code.**

## Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Each person only modifies their own model files.
