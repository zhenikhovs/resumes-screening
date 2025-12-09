import os
from services.hh_auth import get_access_token
from services.hh_fetch_raw import rebuild_raw_resumes, load_json
from services.hh_fetch_full import fetch_full_resumes


def ensure_dirs():
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)


def main():
    ensure_dirs()
    print("🚀 Запуск проекта AI Resume Screening")

    token = get_access_token()

    raw_resumes = rebuild_raw_resumes(token)
    print(f"📦 Всего кратких резюме с query: {len(raw_resumes)}")

    # --- 1. Краткие резюме ---
    # raw_resumes = fetch_all_raw_resumes(token)


    # raw_path = "data/raw/resumes_raw.json"
    # raw_resumes = load_json(raw_path) or []
    # print(f"📦 Загружено {len(raw_resumes)} кратких резюме из файла")
    #
    # # --- 2. Полные резюме ---
    # print("📥 Скачиваем полные резюме (докачивает только недостающие)...")
    # full_resumes = fetch_full_resumes(token, raw_resumes)
    #
    # print("\n🎉 Все этапы завершены. Данные готовы к предобработке!")


if __name__ == "__main__":
    main()
