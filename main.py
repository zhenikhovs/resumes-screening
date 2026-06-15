from config.paths import RAW_PART_RESUMES
from services.api.hh_auth import get_access_token
from services.api.hh_fetch_full import fetch_full_resumes
from services.utils import load_json, save_json

QUERY_FILES_DIR = RAW_PART_RESUMES
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
    QUERY_FILES_DIR.mkdir(parents=True, exist_ok=True)
    from config.paths import PREPARED_DIR
    PREPARED_DIR.mkdir(parents=True, exist_ok=True)

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
    query_path = QUERY_FILES_DIR / query_file

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
