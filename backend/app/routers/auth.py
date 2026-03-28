"""Authentication endpoints. Owned by Backend A."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_researcher, hash_password, verify_password
from app.database import get_db
from app.models.researcher import Researcher
from app.schemas.auth import LoginRequest, RegisterRequest, ResearcherResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=ResearcherResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new researcher account."""
    existing = await db.execute(select(Researcher).where(Researcher.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    researcher = Researcher(
        email=body.email, password_hash=hash_password(body.password), name=body.name
    )
    db.add(researcher)
    await db.flush()
    await db.refresh(researcher)
    return researcher


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and return a JWT token."""
    result = await db.execute(select(Researcher).where(Researcher.email == body.email))
    researcher = result.scalar_one_or_none()
    if not researcher or not verify_password(body.password, researcher.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token, expires_in = create_access_token(researcher.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=ResearcherResponse)
async def get_me(researcher: Researcher = Depends(get_current_researcher)):
    """Return the currently authenticated researcher."""
    return researcher
