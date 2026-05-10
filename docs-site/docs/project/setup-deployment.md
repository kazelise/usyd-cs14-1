# Local Setup & Deployment Prep

## Run The Application Locally

From the repository root:

```bash
docker compose up -d
```

Expected local services:

| Service | URL | Use |
|---|---|---|
| Frontend | `http://localhost:3000` | Researcher admin and participant survey runner |
| Backend API | `http://localhost:8000` | FastAPI application |
| Swagger | `http://localhost:8000/docs` | API exploration and smoke checks |
| ReDoc | `http://localhost:8000/redoc` | API reference |

For host-based development:

```bash
docker compose up db -d
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

## Run This Documentation Site

```bash
cd docs-site
npm install
npm run dev
```

The docs dev server runs on `http://localhost:2999`.

Build verification:

```bash
cd docs-site
npm run build
```

## Local Smoke Test

Before calling a build MVP-ready:

1. Open the frontend and register or sign in as a researcher.
2. Create a survey with a clear title, at least one condition, and calibration settings.
3. Add at least one fetched or manually edited post card.
4. Add question blocks covering the required question types for the study.
5. Export/import a translation template and preview at least English and Chinese.
6. Preview the survey for each condition and language combination that will be tested.
7. Publish the survey and copy the share link.
8. Open the share link in a fresh browser session.
9. Select participant language, grant camera permission, complete calibration, interact with cards, answer questions, and submit.
10. Confirm analytics update and export CSV/JSON with survey, condition, and language filters.

## Deployment Preparation

Actual deployment is postponed. The Japan server deployment is the final step later, after the local MVP acceptance checks pass.

Prepare these items before deployment:

| Area | Checklist |
|---|---|
| Server | Japan host provisioned, SSH access confirmed, firewall allows HTTP/HTTPS, disk space checked. |
| Runtime | Docker and Docker Compose installed, repository checked out, production branch pinned. |
| Environment | Backend secret key, database URL, allowed origins, frontend API base URL, HTTPS domain, and optional tracking configuration documented. |
| Database | Production PostgreSQL volume planned, backup path defined, Alembic migration command tested on staging or disposable database. |
| HTTPS | Browser camera APIs require secure context outside localhost, so production participant links must use HTTPS. |
| CORS | Frontend origin must be explicitly allowed by the backend. |
| Smoke test | Register/login, create survey, metadata fetch/manual card, publish, participant run, calibration, analytics, CSV export, JSON export. |
| Rollback | Previous image/tag retained, database backup captured before migration, logs accessible. |

Deployment should not be treated as complete until the public frontend can reach the public API, camera calibration works in a real participant browser over HTTPS, and exports can be downloaded from the deployed admin interface.
