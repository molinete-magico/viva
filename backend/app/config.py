import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(BACKEND_ROOT / ".env")


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DATA_DIR / 'app.db'}"


class Settings:
    def __init__(self) -> None:
        self.app_name = "Viva"
        self.database_url: str = _database_url()
        self.groq_api_key: str | None = os.getenv("GROQ_API_KEY") or None
        self.groq_model_quick: str = os.getenv("GROQ_MODEL_QUICK") or "openai/gpt-oss-20b"
        self.groq_model_standard: str = os.getenv("GROQ_MODEL_STANDARD") or "openai/gpt-oss-120b"
        self.jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
        self.jwt_algorithm = "HS256"
        self.jwt_expiry_days: int = int(os.getenv("JWT_EXPIRY_DAYS", "14"))
        self.cors_origins: list[str] = _cors_origins()
        self.auto_migrate: bool = os.getenv("AUTO_MIGRATE", "true").lower() == "true"


settings = Settings()
