"""Общие HTTP-заголовки для API hh.ru (обязательный User-Agent с контактом)."""
import os

from dotenv import load_dotenv

load_dotenv()

# Формат по документации hh: App/Version (email@example.com)
_DEFAULT_CONTACT = os.getenv("HH_CONTACT_EMAIL") or os.getenv("WEB_HR_EMAIL", "support@example.com")
_DEFAULT_APP = os.getenv("HH_APP_NAME", "AIResumeScreening/1.0")


def hh_user_agent() -> str:
    contact = _DEFAULT_CONTACT.strip()
    app = _DEFAULT_APP.strip()
    if "(" in app:
        return app
    return f"{app} ({contact})"


def hh_headers(token: str | None = None) -> dict[str, str]:
    headers = {"User-Agent": hh_user_agent()}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
