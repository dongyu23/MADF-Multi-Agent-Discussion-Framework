from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "MADF User Management API"
    API_V1_STR: str = "/api/v1"
    # Use /tmp for SQLite in Vercel environment as it's the only writable directory
    # Note: SQLite in Vercel is not persistent across invocations
    SQLALCHEMY_DATABASE_URI: str = "sqlite:////tmp/madf.db" if os.environ.get("VERCEL") else "sqlite:///./madf.db"

    class Config:
        case_sensitive = True

settings = Settings()
