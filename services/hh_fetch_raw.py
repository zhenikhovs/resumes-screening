import time
import json
import requests
from tqdm import tqdm
import os

QUERIES = [
    "web developer",
    "frontend developer",
    "backend developer",
    "fullstack developer",
    "javascript developer",
    "php developer",
    "project manager",
    "IT project manager"
]

os.makedirs("data/raw", exist_ok=True)


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_pages(query, token, pages=100):
    """Скачиваем много страниц кратких резюме по запросу."""
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ai-resume-screener/1.0"
    }

    results = []

    for page in tqdm(range(pages), desc=f"🔍 {query}"):
        url = f"https://api.hh.ru/resumes?text={query}&page={page}&per_page=20"
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            print(f"⚠ Ошибка {r.status_code}: {r.text}")
            break

        items = r.json().get("items", [])
        results.extend(items)

        time.sleep(0.5)

    return results


def rebuild_raw_resumes(token):
    raw_path = "data/raw/resumes_raw.json"

    # Загружаем старые краткие резюме
    old_resumes = load_json(raw_path)
    print(f"📦 Загружено старых резюме: {len(old_resumes)}")

    # Словарь id → resume
    resume_map = {r["id"]: r for r in old_resumes}

    # Проходим по запросам
    for query in QUERIES:
        print(f"\n🚀 Скачиваем по запросу: {query}")

        fetched = fetch_pages(query, token, pages=100)

        for r in fetched:
            rid = r.get("id")
            if not rid:
                continue

            if rid in resume_map:
                # обновляем query
                resume_map[rid]["query"] = query
            else:
                # новое резюме
                r["query"] = query
                resume_map[rid] = r

    # ❗ ОСТАВЛЯЕМ ТОЛЬКО ТЕ, ГДЕ ЕСТЬ query
    final_resumes = [r for r in resume_map.values() if "query" in r]

    print(f"\n✨ Итог: резюме с указанным query: {len(final_resumes)}")

    save_json(raw_path, final_resumes)

    return final_resumes
