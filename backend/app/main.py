"""CS14-1 Survey Platform API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import auth, surveys, tracking


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="CS14-1 Survey Platform",
    description=(
        "A survey platform for researchers to study how users interact with "
        "social media content. Supports A/B group testing, gaze tracking "
        "(via MediaPipe Face Mesh), and click tracking."
    ),
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Auth",
            "description": "Researcher registration and JWT authentication.",
        },
        {
            "name": "Surveys",
            "description": "Survey CRUD, post management, and participant endpoints.",
        },
        {
            "name": "Tracking (Backend C)",
            "description": (
                "Webcam calibration, continuous gaze tracking, and mouse click "
                "tracking. Data is collected during survey participation and "
                "stored for later analysis."
            ),
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(surveys.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
