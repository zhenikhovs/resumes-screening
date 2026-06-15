import requests
from tqdm import tqdm

from config.paths import RAW_FULL_RESUMES, RAW_RESUMES
from services.utils import load_json, save_json, setup_logger

RAW_FULL_RESUMES.mkdir(parents=True, exist_ok=True)
RAW_RESUMES.mkdir(parents=True, exist_ok=True)


def fetch_full_resumes(token, query_resumes, query_name):
    """
    Загружает полные резюме для краткого списка query_resumes.

    query_name — ключ файла: data/raw/full/resumes/resumes_{query_name}.json
    (пробелы → подчёркивания). Для CLI: «backend developer»;
    для веб-кампании всегда передавайте slug вида camp_12, как в part/resumes.
    """
    logger = setup_logger(str(RAW_FULL_RESUMES / "fetch_full.log"))

    from services.api.hh_http import hh_headers

    headers = hh_headers(token)

    full_path = RAW_FULL_RESUMES / "resumes_full.json"
    full_resumes = load_json(full_path) or []

    downloaded_ids = {r.get("id") for r in full_resumes if "id" in r}
    print(f"📌 Уже скачано полных резюме: {len(downloaded_ids)}")

    query_suffix = query_name.replace(" ", "_")
    query_row_path = RAW_RESUMES / f"resumes_{query_suffix}.json"
    query_full_path = RAW_FULL_RESUMES / f"resumes_{query_suffix}.json"
    query_full = load_json(query_full_path) or []

    for short_res in tqdm(query_resumes, desc=f"📥 Получение полных резюме для {query_name}"):
        rid = short_res.get("id")
        if not rid:
            continue

        if rid in downloaded_ids:
            for r in full_resumes:
                if r.get("id") == rid:
                    r["query"] = query_name
                    if not any(q.get("id") == rid for q in query_full):
                        query_full.append(r)
                    break
            save_json(full_path, full_resumes)
            save_json(query_full_path, query_full)
            continue

        try:
            resp = requests.get(f"https://api.hh.ru/resumes/{rid}", headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠ Ошибка запроса {rid}: {e}")
            continue

        if resp.status_code == 200:
            full_r = resp.json()
            full_r["query"] = query_name
            full_resumes.append(full_r)
            query_full.append(full_r)
            downloaded_ids.add(rid)
            logger.info(f"✅ Скачано резюме {rid}")
            save_json(full_path, full_resumes)
            save_json(query_full_path, query_full)
        elif resp.status_code == 404:
            logger.warning(f"⚠ 404 — резюме {rid} не найдено")
            query_resumes = [s for s in query_resumes if s.get("id") != rid]
            save_json(query_row_path, query_resumes)
        elif resp.status_code == 429:
            logger.warning("⚠ 429 — лимит достигнут, прекращаем выполнение.")
            raise SystemExit("Лимит API достигнут. Скрипт завершён.")
        else:
            logger.warning(f"⚠ Ошибка {resp.status_code} для {rid}: {resp.text}")

    save_json(full_path, full_resumes)
    save_json(query_full_path, query_full)
    print(f"\n📦 Всего полных резюме для {query_name}: {len(query_full)}")
    print(f"📦 Всего в базе full_resumes: {len(full_resumes)}")
    return full_resumes
