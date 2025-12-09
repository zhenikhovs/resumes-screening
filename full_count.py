import json
import os
from collections import defaultdict

RAW_PATH = "data/raw/resumes_raw.json"
FULL_PATH = "data/processed/resumes_full.json"

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def main():
    raw_resumes = load_json(RAW_PATH)
    full_resumes = load_json(FULL_PATH)

    # Словарь id -> query
    id_to_query = {r["id"]: r["query"] for r in raw_resumes if "query" in r}

    # Считаем полные резюме по query
    counts = defaultdict(int)
    for r in full_resumes:
        rid = r.get("id")
        if rid in id_to_query:
            counts[id_to_query[rid]] += 1

    print("📊 Полные резюме по запросам:")
    for query, count in counts.items():
        print(f"  → {query}: {count}")

if __name__ == "__main__":
    main()
