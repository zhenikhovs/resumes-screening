import os
import json

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

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

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def main():
    # --------------------------
    # 1️⃣ Полные резюме
    # --------------------------
    full_resumes_path = os.path.join(PROCESSED_DIR, "resumes_full.json")
    full_resumes = load_json(full_resumes_path)
    full_ids = {r.get("id") for r in full_resumes if "id" in r}

    print(f"📦 Всего полных резюме в файле: {len(full_resumes)}")
    print(f"✅ Уникальных полных резюме: {len(full_ids)}\n")

    # --------------------------
    # 2️⃣ Краткие резюме по запросам
    # --------------------------
    print("📊 Распределение кратких резюме по запросам:")
    for query in QUERIES:
        file_path = os.path.join(RAW_DIR, f"resumes_{query}.json")
        resumes = load_json(file_path)
        print(f"  {query}: {len(resumes)} резюме")

if __name__ == "__main__":
    main()
