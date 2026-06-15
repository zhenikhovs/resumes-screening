import time
import requests
from tqdm import tqdm

from config.paths import PREPARED_DIR, RAW_VACANCIES
from services.utils import save_json, setup_logger

RAW_VACANCIES.mkdir(parents=True, exist_ok=True)
HH_API = "https://api.hh.ru/vacancies"


def fetch_vacancies(token, queries, per_query=100):
    """
    Скачивает вакансии по списку query. На каждый query — отдельный файл.
    queries: list[str], per_query: int
    """
    logger = setup_logger(str(PREPARED_DIR / "fetch_vacancies.log"))
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ai-resume-screener/1.0"
    }

    for query in queries:
        print(f"\n🚀 Получение вакансий для query: {query}")
        collected = []
        page = 0
        per_page = 20
        max_pages = per_query // per_page

        while page < max_pages:
            params = {"text": query, "page": page, "per_page": per_page}
            resp = requests.get(HH_API, headers=headers, params=params)

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break
                for v in items:
                    v["query"] = query
                    collected.append(v)
                page += 1
                time.sleep(0.5)
            elif resp.status_code == 429:
                logger.warning("⚠ 429 — лимит API, прекращаем выполнение")
                raise SystemExit("API лимит исчерпан")
            else:
                logger.warning(f"⚠ Ошибка {resp.status_code}: {resp.text}")
                break

        path = RAW_VACANCIES / f"vacancies_{query.replace(' ', '_')}.json"
        save_json(path, collected)
        print(f"📦 Сохранено вакансий: {len(collected)} → {path}")
