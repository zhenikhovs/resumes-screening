import time
import requests
from tqdm import tqdm
import os
from services.utils import load_json, save_json, setup_logger

os.makedirs("data/prepared", exist_ok=True)
os.makedirs("data/raw/resumes", exist_ok=True)  # Для кратких вакансий

def fetch_full_vacancies(token, query_vacancies, query_name):
    """
    Загружает полные вакансии для конкретного запроса (query_name).

    query_vacancies: list кратких вакансий, полученных для query_name
    query_name: str, например 'backend developer'
    """
    logging = setup_logger(f"data/prepared/fetch_full_vacancies.log")

    query_row_path = f"data/raw/vacancies/vacancies_{query_name.replace(' ', '_')}.json"
    query_prepared_path = f"data/prepared/vacancies/vacancies_{query_name.replace(' ', '_')}.json"
    os.makedirs(os.path.dirname(query_prepared_path), exist_ok=True)
    query_full = load_json(query_prepared_path) or []

    downloaded_ids = {v.get("id") for v in query_full if "id" in v}
    print(f"📌 Уже скачано вакансий для {query_name}: {len(downloaded_ids)}")

    for short_vac in tqdm(query_vacancies, desc=f"📥 Получение полных вакансий для {query_name}"):
        vid = short_vac.get("id")
        if not vid or vid in downloaded_ids:
            continue

        try:
            resp = requests.get(f"https://api.hh.ru/vacancies/{vid}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        except requests.exceptions.RequestException as e:
            logging.warning(f"⚠ Ошибка запроса {vid}: {e}")
            continue

        if resp.status_code == 200:
            full_vac = resp.json()
            full_vac["query"] = query_name
            query_full.append(full_vac)
            downloaded_ids.add(vid)
            logging.info(f"✅ Скачана вакансия {vid}")
            save_json(query_prepared_path, query_full)

        elif resp.status_code == 404:
            logging.warning(f"⚠ 404 — вакансия {vid} не найдена")
            query_vacancies = [v for v in query_vacancies if v.get("id") != vid]
            save_json(query_row_path, query_vacancies)

        elif resp.status_code == 429:
            logging.warning(f"⚠ 429 — лимит достигнут, прекращаем выполнение.")
            raise SystemExit("Лимит API достигнут. Скрипт завершён.")

        else:
            logging.warning(f"⚠ Ошибка {resp.status_code} для {vid}: {resp.text}")
            continue

    print(f"\n📦 Всего полных вакансий для {query_name}: {len(query_full)}")
    return query_full
