import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-use-long-random-string")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

WEB_HR_EMAIL = os.getenv("WEB_HR_EMAIL", "hr@example.com")
WEB_HR_PASSWORD = os.getenv("WEB_HR_PASSWORD", "hr12345")

RANKING_METHOD = os.getenv("RANKING_METHOD", "e5")
RANKING_CE_MODEL = os.getenv("RANKING_CE_MODEL", "russian")
RANKING_TOP_N = int(os.getenv("RANKING_TOP_N", "5"))
USE_CACHED_RANKING = os.getenv("USE_CACHED_RANKING", "true").lower() in ("1", "true", "yes")

# Кампания: сбор с hh (3×20 в выдаче → до 50 полных резюме на ранжирование)
CAMPAIGN_RESUME_SEARCH_PAGES = int(os.getenv("CAMPAIGN_RESUME_SEARCH_PAGES", "3"))
CAMPAIGN_MAX_FULL_RESUMES = int(os.getenv("CAMPAIGN_MAX_FULL_RESUMES", "50"))
CAMPAIGN_DEMO_FALLBACK_QUERY = os.getenv("CAMPAIGN_DEMO_FALLBACK_QUERY", "backend_developer")

# Почта (приглашения кандидатам)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@ai-resume.local")
APP_PUBLIC_URL = os.getenv("APP_PUBLIC_URL", "http://localhost:5173")

UPLOAD_DIR = PROJECT_ROOT / "data" / "interviews"
SCENARIOS_DIR = PROJECT_ROOT / "data" / "interviews" / "scenarios"
CAMPAIGNS_DATA_DIR = PROJECT_ROOT / "data" / "campaigns"
