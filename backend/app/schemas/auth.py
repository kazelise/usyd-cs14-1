from datetime import datetime

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ResearcherResponse(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}


class UpdateResearcherRequest(BaseModel):
    name: str
