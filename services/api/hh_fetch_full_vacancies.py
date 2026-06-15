import requests
from tqdm import tqdm

from config.paths import RAW_FULL_VACANCIES, RAW_VACANCIES
from services.utils import load_json, save_json, setup_logger

RAW_FULL_VACANCIES.mkdir(parents=True, exist_ok=True)
RAW_VACANCIES.mkdir(parents=True, exist_ok=True)


def fetch_full_vacancies(token, query_vacancies, query_name):
    """
    Загружает полные вакансии для конкретного запроса (query_name).
    """
    logger = setup_logger(str(RAW_FULL_VACANCIES / "fetch_full_vacancies.log"))

    query_suffix = query_name.replace(" ", "_")
    query_row_path = RAW_VACANCIES / f"vacancies_{query_suffix}.json"
    query_full_path = RAW_FULL_VACANCIES / f"vacancies_{query_suffix}.json"
    query_full = load_json(query_full_path) or []

    downloaded_ids = {v.get("id") for v in query_full if "id" in v}
    print(f"📌 Уже скачано вакансий для {query_name}: {len(downloaded_ids)}")

    headers = {"Authorization": f"Bearer {token}", "User-Agent": "ai-resume-screener/1.0"}

    for short_vac in tqdm(query_vacancies, desc=f"📥 Получение полных вакансий для {query_name}"):
        vid = short_vac.get("id")
        if not vid or vid in downloaded_ids:
            continue

        try:
            resp = requests.get(
                f"https://api.hh.ru/vacancies/{vid}", headers=headers, timeout=10
            )
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠ Ошибка запроса {vid}: {e}")
            continue

        if resp.status_code == 200:
            full_vac = resp.json()
            full_vac["query"] = query_name
            query_full.append(full_vac)
            downloaded_ids.add(vid)
            logger.info(f"✅ Скачана вакансия {vid}")
            save_json(query_full_path, query_full)
        elif resp.status_code == 404:
            logger.warning(f"⚠ 404 — вакансия {vid} не найдена")
            query_vacancies = [v for v in query_vacancies if v.get("id") != vid]
            save_json(query_row_path, query_vacancies)
        elif resp.status_code == 429:
            logger.warning("⚠ 429 — лимит достигнут, прекращаем выполнение.")
            raise SystemExit("Лимит API достигнут. Скрипт завершён.")
        else:
            logger.warning(f"⚠ Ошибка {resp.status_code} для {vid}: {resp.text}")

    print(f"\n📦 Всего полных вакансий для {query_name}: {len(query_full)}")
    return query_full
