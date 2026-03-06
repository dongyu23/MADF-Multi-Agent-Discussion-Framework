from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "MADF User Management API"
    API_V1_STR: str = "/api/v1"
    
    # Priority:
    # 1. Turso (libsql) via TURSO_DATABASE_URL
    # 2. Postgres via POSTGRES_URL/DATABASE_URL
    # 3. Vercel SQLite (Temporary /tmp)
    # 4. Local SQLite (./)
    
    @staticmethod
    def _get_database_url():
        # 1. Turso (libsql)
        turso_url = os.environ.get("TURSO_DATABASE_URL")
        turso_token = os.environ.get("TURSO_AUTH_TOKEN")
        if turso_url and turso_token:
            # Check if it is a libsql protocol URL
            if turso_url.startswith("libsql://"):
                # Use sqlite+libsql:// protocol for SQLAlchemy
                turso_url = turso_url.replace("libsql://", "sqlite+libsql://", 1)
            elif not turso_url.startswith("sqlite+libsql://"):
                # If it's just https://... or other, assume it needs sqlite+libsql:// prefix if it's Turso
                # But Turso usually gives libsql:// or https://. 
                # If https, it might be hrana over http. 
                # Safe bet for sqlalchemy-libsql is sqlite+libsql://
                if turso_url.startswith("https://"):
                    turso_url = "sqlite+libsql://" + turso_url.split("://", 1)[1]
            
            # Append auth token
            return f"{turso_url}?authToken={turso_token}&secure=true"
            
        # 2. Postgres
        pg_url = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
        if pg_url:
            if pg_url.startswith("postgres://"):
                return pg_url.replace("postgres://", "postgresql://", 1)
            return pg_url
            
        # 3. Vercel SQLite (Fallback)
        if os.environ.get("VERCEL"):
            return "sqlite:////tmp/madf.db"
            
        # 4. Local SQLite (Dev)
        return "sqlite:///./madf.db"

    SQLALCHEMY_DATABASE_URI: str = _get_database_url()

    class Config:
        case_sensitive = True

settings = Settings()
