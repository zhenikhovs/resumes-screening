import time
import requests
from tqdm import tqdm
import os
from services.utils import load_json, save_json, setup_logger

os.makedirs("data/processed", exist_ok=True)
os.makedirs("data/raw/queries", exist_ok=True)  # Для файлов по query

def fetch_full_resumes(token, query_resumes, query_name):
    """
    Загружает полные резюме для конкретного запроса (query_name).

    query_resumes: list кратких резюме, полученных для query_name
    query_name: str, например 'backend developer'
    """
    logging = setup_logger("data/processed/fetch_full.log")

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ai-resume-screener/1.0"
    }

    full_path = "data/processed/resumes_full.json"
    full_resumes = load_json(full_path) or []

    # ID уже скачанных резюме
    downloaded_ids = {r.get("id") for r in full_resumes if "id" in r}

    print(f"📌 Уже скачано полных резюме: {len(downloaded_ids)}")

    query_file_path = f"data/raw/queries/resumes_{query_name.replace(' ', '_')}.json"
    query_full = load_json(query_file_path) or []

    for short_res in tqdm(query_resumes, desc=f"📥 Получение полных резюме для {query_name}"):
        rid = short_res.get("id")
        if not rid:
            continue

        # Если резюме уже скачано, обновляем query в общем файле и в файле query
        if rid in downloaded_ids:
            # Обновляем query в общем списке
            for r in full_resumes:
                if r.get("id") == rid:
                    r["query"] = query_name
                    break
            # Обновляем query в query_full
            found = False
            for r in query_full:
                if r.get("id") == rid:
                    r["query"] = query_name
                    found = True
                    break
            if not found:
                # Добавляем в query_full, если не было
                r = next(r for r in full_resumes if r.get("id") == rid)
                query_full.append(r)
            # Сохраняем после обновления
            save_json(full_path, full_resumes)
            save_json(query_file_path, query_full)
            continue

        # Скачиваем новое резюме
        try:
            resp = requests.get(f"https://api.hh.ru/resumes/{rid}", headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            logging.warning(f"⚠ Ошибка запроса {rid}: {e}")
            continue

        if resp.status_code == 200:
            full_r = resp.json()
            full_r["query"] = query_name
            full_resumes.append(full_r)
            query_full.append(full_r)
            downloaded_ids.add(rid)
            logging.info(f"✅ Скачано резюме {rid}")
            # Сохраняем сразу после успешного скачивания
            save_json(full_path, full_resumes)
            save_json(query_file_path, query_full)

        elif resp.status_code == 404:
            logging.warning(f"⚠ 404 — резюме {rid} не найдено")
            # удаляем резюме из query_resumes и из общего списка, если есть
            query_resumes.remove(short_res)
            full_resumes = [r for r in full_resumes if r.get("id") != rid]
            save_json(full_path, full_resumes)
            save_json(query_file_path, query_full)

        elif resp.status_code == 429:
            logging.warning(f"⚠ 429 — лимит достигнут, прекращаем выполнение.")
            # Завершаем скрипт без ожидания, лимит восстанавливается через 24 часа
            raise SystemExit("Лимит API достигнут. Скрипт завершён.")

        else:
            logging.warning(f"⚠ Ошибка {resp.status_code} для {rid}: {resp.text}")
            continue

        time.sleep(0.5)

    # Финальное сохранение на всякий случай
    save_json(full_path, full_resumes)
    save_json(query_file_path, query_full)

    print(f"\n📦 Всего полных резюме для {query_name}: {len(query_full)}")
    print(f"📦 Всего в базе full_resumes: {len(full_resumes)}")

    return full_resumes
