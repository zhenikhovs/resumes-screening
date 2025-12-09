import json
import os
from services.hh_fetch_raw import load_json, save_json, QUERIES

RAW_PATH = "data/raw/resumes_raw.json"
OUTPUT_DIR = "data/raw/queries"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def split_resumes_by_query():
    # Загружаем все краткие резюме
    all_resumes = load_json(RAW_PATH)
    if not all_resumes:
        print("❌ Нет резюме для обработки")
        return

    print(f"📦 Всего резюме для разделения: {len(all_resumes)}")

    # Для каждого запроса собираем свои резюме
    for query in QUERIES:
        query_resumes = [r for r in all_resumes if r.get("query") == query]
        save_json(os.path.join(OUTPUT_DIR, f"resumes_{query.replace(' ', '_')}.json"), query_resumes)
        print(f"✔ {query}: {len(query_resumes)} резюме сохранено")

    print("\n🎉 Разделение резюме по файлам завершено!")

if __name__ == "__main__":
    split_resumes_by_query()
