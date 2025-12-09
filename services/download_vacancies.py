import os
import json
import time
import requests
from pathlib import Path

QUERIES = [
    "python developer",
    "machine learning engineer",
    "data scientist",
    "data analyst",
    "backend developer",
    "django developer",
]

SAVE_PATH = Path("data/raw/vacancies_raw.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)",
}


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_vacancies_for_query(query):
    print(f"\n🔎 Собираем вакансии по запросу: {query}")

    page = 0
    results = []

    while True:
        resp = requests.get(
            "https://api.hh.ru/vacancies",
            params={
                "text": query,
                "page": page,
                "per_page": 100,
            },
            headers=HEADERS,
        )

        if resp.status_code == 429:
            print("⏳ Лимит! Ждём 60 сек...")
            time.sleep(60)
            continue

        resp.raise_for_status()
        data = resp.json()

        items = data.get("items", [])
        if not items:
            break

        results.extend(items)

        print(f"  → страница {page+1}: {len(items)} вакансий")

        if page >= data.get("pages", 0) - 1:
            break

        page += 1
        time.sleep(0.3)

    print(f"✅ Всего собрано: {len(results)}")

    return results


def main():
    existing = load_json(SAVE_PATH)
    existing_ids = {v["id"] for v in existing}

    print(f"📦 Уже сохранено вакансий: {len(existing)}")

    all_new_vacancies = []

    for q in QUERIES:
        vacancies = fetch_vacancies_for_query(q)

        for v in vacancies:
            if v["id"] not in existing_ids:
                all_new_vacancies.append(v)
                existing_ids.add(v["id"])

    print(f"\n✨ Новых вакансий: {len(all_new_vacancies)}")

    save_json(SAVE_PATH, existing + all_new_vacancies)

    print(f"📁 Saved to: {SAVE_PATH}")


if __name__ == "__main__":
    main()
