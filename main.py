import os
from services.hh_auth import get_access_token
from services.utils import load_json, save_json
from services.hh_fetch_full import fetch_full_resumes

QUERY_FILES_DIR = "data/raw/part/resumes"
QUERIES = [
    "web developer",
    "frontend developer",
    "php developer",
    "IT project manager",
    "javascript developer",
    "backend developer",
    "fullstack developer",
    "project manager"
]

def ensure_dirs():
    os.makedirs("data/raw/part/resumes", exist_ok=True)
    os.makedirs("data/prepared", exist_ok=True)

def main():
    ensure_dirs()
    print("🚀 Запуск проекта AI Resume Screening")

    token = get_access_token()

    # --- Ввод query вручную ---
    query_name = QUERIES[4]
    if not query_name:
        print("❌ Не задан query")
        return

    query_file = f"resumes_{query_name.replace(' ', '_')}.json"
    query_path = os.path.join(QUERY_FILES_DIR, query_file)

    short_resumes = load_json(query_path) or []
    print(f"📦 Кратких резюме в файле '{query_file}': {len(short_resumes)}")

    if not short_resumes:
        print("⚠ Пустой файл, пропускаем.")
        return

    # --- Скачиваем полные резюме ---
    fetch_full_resumes(token, short_resumes, query_name)

    print("\n🎉 Этап завершён. Данные готовы к предобработке!")

if __name__ == "__main__":
    main()
