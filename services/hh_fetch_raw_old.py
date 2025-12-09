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
    return None


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_raw(query, token, existing_ids=None, pages=10):
    if existing_ids is None:
        existing_ids = set()

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ai-resume-screener/1.0"
    }

    new_resumes = []

    for page in tqdm(range(pages), desc=f"🔍 {query}"):
        url = f"https://api.hh.ru/resumes?text={query}&page={page}&per_page=20"
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            print(f"⚠ Ошибка {r.status_code}: {r.text}")
            break

        items = r.json().get("items", [])

        for resume in items:
            rid = resume.get("id")
            if rid and rid not in existing_ids:
                resume["query"] = query   # ← ← ← ВАЖНО! ДОБАВЛЯЕМ ПОЛЕ
                new_resumes.append(resume)
                existing_ids.add(rid)

        time.sleep(1)

    print(f"✔ Найдено новых резюме по '{query}': {len(new_resumes)}")
    return new_resumes, existing_ids



def fetch_all_raw_resumes(token):
    raw_path = "data/raw/resumes_raw.json"
    ids_path = "data/raw/resumes_ids.json"

    all_resumes = load_json(raw_path) or []
    existing_ids = set(load_json(ids_path) or [])

    for query in QUERIES:
        new_resumes, existing_ids = fetch_raw(query, token, existing_ids, pages=10)
        all_resumes.extend(new_resumes)
        prev = load_json(f"data/raw/resumes_{query}.json") or []
        prev.extend(new_resumes)
        save_json(f"data/raw/resumes_{query}.json", prev)

    save_json(raw_path, all_resumes)
    save_json(ids_path, list(existing_ids))

    print(f"\n📦 Всего кратких резюме в базе: {len(all_resumes)}")
    return all_resumes
