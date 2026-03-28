# CS14-1: Social Media Survey Platform

> COMP5703 Capstone — University of Sydney, S1 2026

A survey platform for researchers to study how users interact with social media content (e.g., fake news trust studies). Researchers paste news article URLs, the platform auto-generates simulated social media post cards with controllable engagement numbers (likes, comments, shares). Supports A/B group testing, gaze tracking, and click tracking.

## Quick Start

```bash
docker compose up -d
```

| Service         | URL                          |
| --------------- | ---------------------------- |
| Frontend        | http://localhost:3000         |
| Backend API     | http://localhost:8000         |
| Swagger Docs    | http://localhost:8000/docs    |

## Tech Stack

| Layer    | Technology                                 |
| -------- | ------------------------------------------ |
| Frontend | Next.js 14 · TypeScript · Tailwind CSS     |
| Backend  | FastAPI · SQLAlchemy 2.0 · Pydantic        |
| Database | PostgreSQL 16                              |
| Tracking | MediaPipe Face Mesh (browser) · WebRTC     |
| DevOps   | Docker Compose · GitHub Actions CI         |

## Core Features

1. **Link-based post creation** — Researcher pastes a URL, platform fetches OG metadata
2. **Controllable variables** — Researcher sets fake likes, comments, shares, overrides headline/image
3. **Fake comments** — Researcher manually writes comment content for posts
4. **A/B testing** — Random group assignment, conditional post visibility per group
5. **Participant interaction** — Like, comment, click to original article (all captured)
6. **Gaze tracking** — Continuous XY coordinate capture during survey participation
7. **Click tracking** — Mouse click positions recorded with target element identification
8. **Data export** — CSV export of all collected data per survey

## Team & Module Ownership

| Role            | Module                                     |
| --------------- | ------------------------------------------ |
| Frontend A (×2) | Researcher admin UI (survey editor)        |
| Frontend B (×2) | Participant survey page (social feed)      |
| Backend A/B (×2)| Auth · Survey/Post CRUD · OG fetch · Export|
| Backend C (×2)  | Calibration · Gaze tracking · Click tracking|

## Git Workflow

1. All work on **feature branches** off `dev`
2. Open **Pull Request** to `dev` — direct push blocked
3. **1 approval** required · CI must pass
4. **Squash merge** to keep history clean

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
