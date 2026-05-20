from pydantic import model_validator
from pydantic_settings import BaseSettings

_UNSAFE_DEFAULT_KEY = "dev-secret-change-in-production"


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://cs14:cs14_dev_password@localhost:5432/cs14_survey"
    SECRET_KEY: str = _UNSAFE_DEFAULT_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    )
    DEBUG: bool = False

    @model_validator(mode="after")
    def _reject_unsafe_key_in_prod(self) -> "Settings":
        if not self.DEBUG and self.SECRET_KEY == _UNSAFE_DEFAULT_KEY:
            raise ValueError(
                "SECRET_KEY must not be the default demo value when DEBUG=false. "
                "Set a strong SECRET_KEY in your environment or .env file."
            )
        return self

    class Config:
        env_file = ".env"


settings = Settings()
