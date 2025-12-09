import time
import json
import requests
from tqdm import tqdm
import os

os.makedirs("data/processed", exist_ok=True)


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_full_resumes(token, raw_resumes):
    import logging

    logging.basicConfig(
        level=logging.INFO,
        filename="data/processed/fetch_full.log",
        filemode="a",
        format="%(asctime)s %(levelname)s:%(message)s"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ai-resume-screener/1.0"
    }

    # Загружаем уже скачанные полные резюме
    full_path = "data/processed/resumes_full.json"
    raw_path = "data/raw/resumes_raw.json"
    full_resumes = load_json(full_path) or []

    # Создаём множество ID уже скачанных резюме
    downloaded_ids = {r.get("id") for r in full_resumes if "id" in r}

    print(f"📌 Уже скачано полных резюме: {len(downloaded_ids)}")

    wait_seconds_error = 60    # фиксированная задержка при 429
    wait_seconds = 300    # фиксированная задержка при 429
    max_retries = 5
    save_every = 1      # частичное сохранение

    new_count = 0

    for idx, short_res in enumerate(tqdm(raw_resumes, desc="📥 Получение полных резюме")):
        rid = short_res.get("id")
        if not rid:
            continue

        # Если резюме уже скачано — пропускаем
        if rid in downloaded_ids:
            continue

        url = f"https://api.hh.ru/resumes/{rid}"
        retry = 0

        while retry < max_retries:
            try:
                resp = requests.get(url, headers=headers, timeout=10)
            except requests.exceptions.RequestException as e:
                logging.warning(f"⚠ Ошибка запроса {rid}: {e}")
                retry += 1
                time.sleep(wait_seconds_error)
                continue

            if resp.status_code == 200:
                full_resumes.append(resp.json())
                downloaded_ids.add(rid)
                new_count += 1
                logging.info(f"✅ Скачано резюме {rid}")
                break

            elif resp.status_code == 404:
                logging.warning(f"⚠ 404 — резюме {rid} не найдено")
                raw_resumes.remove(short_res)
                save_json(raw_path, raw_resumes)
                break

            elif resp.status_code == 429:
                logging.warning(
                    f"⚠ 429 (лимит). Резюме {rid}. Повтор {retry + 1}/{max_retries}. "
                    f"Ждём {wait_seconds} секунд."
                )
                retry += 1
                time.sleep(wait_seconds)

            else:
                logging.warning(f"⚠ Ошибка {resp.status_code} для {rid}: {resp.text}")
                break

        # Сохраняем прогресс
        if new_count % save_every == 0 and new_count > 0:
            save_json(full_path, full_resumes)

        time.sleep(0.5)

    # Финальное сохранение
    save_json(full_path, full_resumes)

    print(f"📦 Новых полных резюме скачано: {new_count}")
    print(f"📦 Всего теперь в базе: {len(full_resumes)}")

    return full_resumes
