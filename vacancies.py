import os
from services.hh_auth import get_access_token
from services.utils import load_json, save_json
from services.hh_fetch_full_vacancies import fetch_full_vacancies  # твой новый скрипт для вакансий

QUERY_FILES_DIR = "data/raw/part/vacancies"
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
    os.makedirs("data/raw/part/vacancies", exist_ok=True)
    os.makedirs("data/raw/full/vacancies", exist_ok=True)

def main():
    ensure_dirs()
    print("🚀 Запуск проекта AI Vacancy Screening")

    token = get_access_token()

    query_name = QUERIES[7]
    if not query_name:
        print("❌ Не задан query")
        return

    query_file = f"vacancies_{query_name.replace(' ', '_')}.json"
    query_path = os.path.join(QUERY_FILES_DIR, query_file)

    short_vacancies = load_json(query_path) or []
    print(f"📦 Кратких вакансий в файле '{query_file}': {len(short_vacancies)}")

    if not short_vacancies:
        print("⚠ Пустой файл, пропускаем.")
        return
    # --- Скачиваем полные вакансии ---
    fetch_full_vacancies(token, short_vacancies, query_name)


    print("\n🎉 Этап завершён. Полные вакансии готовы к предобработке!")

if __name__ == "__main__":
    main()
