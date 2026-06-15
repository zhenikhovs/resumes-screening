import os
import urllib.parse
import requests
import webbrowser
from dotenv import load_dotenv
import json

from config.paths import TOKEN_FILE

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


def get_access_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("❌ CLIENT_ID или CLIENT_SECRET отсутствуют в .env")

    token = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            token = data.get("access_token")

    if token and check_token_valid(token):
        print("✅ Используется действующий токен")
        return token

    params = {"response_type": "code", "client_id": CLIENT_ID}
    auth_url = "https://hh.ru/oauth/authorize?" + urllib.parse.urlencode(params)

    try:
        webbrowser.open(auth_url)
    except Exception:
        print("Откройте ссылку вручную:", auth_url)

    code = input("👉 Вставьте параметр code из URL: ").strip()
    if not code:
        raise ValueError("❌ Не введён code")

    resp = requests.post(
        "https://hh.ru/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump({"access_token": token}, f)

    print("✅ Новый access token получен")
    return token


def check_token_valid(token: str) -> bool:
    """Проверяет валидность токена через API HH."""
    from services.api.hh_http import hh_headers

    headers = hh_headers(token)
    test_url = "https://api.hh.ru/me"
    try:
        resp = requests.get(test_url, headers=headers, timeout=10)
        return resp.status_code == 200
    except requests.RequestException:
        return False
