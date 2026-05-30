from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    # max_length 72: bcrypt only hashes the first 72 bytes; longer inputs are
    # silently truncated or raise in newer backends, so reject them up front.
    password: str = Field(min_length=8, max_length=72)
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
