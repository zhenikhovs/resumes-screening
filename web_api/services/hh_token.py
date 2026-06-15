"""Токен HH из data/token.json (без интерактивного OAuth в веб-процессе)."""
import json

from config.paths import TOKEN_FILE
from services.api.hh_auth import check_token_valid

REAUTH_HINT = (
    "Переавторизуйтесь (нужны CLIENT_ID и CLIENT_SECRET в .env):\n"
    '  python -c "from services.api.hh_auth import get_access_token; get_access_token()"'
)


def get_stored_hh_token() -> str | None:
    token, _err = resolve_hh_token()
    return token


def resolve_hh_token() -> tuple[str | None, str | None]:
    """
    (token, error_message).
    token — действующий access_token.
    error — файл есть, но токен отсутствует/невалиден (нужна переавторизация, не demo).
    Оба None — файла token.json нет (допустим demo-режим).
    """
    if not TOKEN_FILE.exists():
        return None, None
    with open(TOKEN_FILE, encoding="utf-8") as f:
        data = json.load(f)
    token = (data.get("access_token") or "").strip()
    if not token:
        return None, f"В {TOKEN_FILE} нет access_token.\n{REAUTH_HINT}"
    if not check_token_valid(token):
        return None, f"Токен HeadHunter недействителен или истёк.\n{REAUTH_HINT}"
    return token, None
