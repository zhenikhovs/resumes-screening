import os
import urllib.parse
import requests
import webbrowser
from dotenv import load_dotenv
import json

# Загружает переменные CLIENT_ID и CLIENT_SECRET из файла .env
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TOKEN_FILE = "data/token.json"  # где будем хранить токен между запусками


def get_access_token():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("❌ CLIENT_ID или CLIENT_SECRET отсутствуют в .env")

    # --- 1. Попытка взять существующий токен ---
    token = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            token = data.get("access_token")

    if token and check_token_valid(token):
        print("✅ Используется действующий токен")
        return token

    # --- 2. Если токен отсутствует или недействителен, получаем новый ---
    params = {"response_type": "code", "client_id": CLIENT_ID}
    auth_url = "https://hh.ru/oauth/authorize?" + urllib.parse.urlencode(params)

    try:
        webbrowser.open(auth_url)
    except:
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

    # Сохраняем токен для будущих запусков
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump({"access_token": token}, f)

    print("✅ Новый access token получен")
    return token


def check_token_valid(token: str) -> bool:
    """Проверяет валидность токена через API HH."""
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ai-resume-screener/1.0"
    }
    test_url = "https://api.hh.ru/me"

    try:
        resp = requests.get(test_url, headers=headers, timeout=10)
        return resp.status_code == 200
    except requests.RequestException:
        return False
