"""CS14-1 Survey Platform API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.config import settings
from app.routers import auth, surveys, tracking


app = FastAPI(
    title="CS14-1 Survey Platform",
    description="Social media survey platform with gaze & click tracking.",
    version="0.1.0",
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
