import time
import requests
from tqdm import tqdm

from config.paths import RAW_DIR
from services.utils import load_json, save_json

QUERIES = ["javascript developer"]
RAW_DIR.mkdir(parents=True, exist_ok=True)


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
    raw_path = RAW_DIR / "resumes_raw.json"
    old_resumes = load_json(raw_path)
    print(f"📦 Загружено старых резюме: {len(old_resumes)}")
    resume_map = {r["id"]: r for r in old_resumes}

    for query in QUERIES:
        print(f"\n🚀 Скачиваем по запросу: {query}")
        fetched = fetch_pages(query, token, pages=100)
        for r in fetched:
            rid = r.get("id")
            if not rid:
                continue
            if rid in resume_map:
                resume_map[rid]["query"] = query
            else:
                r["query"] = query
                resume_map[rid] = r

    final_resumes = [r for r in resume_map.values() if "query" in r]
    print(f"\n✨ Итог: резюме с указанным query: {len(final_resumes)}")
    save_json(raw_path, final_resumes)
    return final_resumes
