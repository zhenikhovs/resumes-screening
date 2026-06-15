"""Сбор данных с HH и подготовка под пайплайн ранжирования (как в run.py)."""
import shutil
import time
import urllib.parse
from pathlib import Path

import requests

from config.paths import (
    RAW_FULL_RESUMES,
    RAW_FULL_VACANCIES,
    RAW_PART_RESUMES,
)
from services.api.hh_fetch_full import fetch_full_resumes
from services.preprocessing.pre_clean_vacancies import clean_vacancy as pre_clean_vacancy
from services.utils import load_json, save_json
from web_api.config import (
    CAMPAIGN_DEMO_FALLBACK_QUERY,
    CAMPAIGN_MAX_FULL_RESUMES,
    CAMPAIGN_RESUME_SEARCH_PAGES,
)
from web_api.services.hh_fetch import fetch_vacancy_by_id
from web_api.services.hh_token import resolve_hh_token
from web_api.services.preprocess_slug import pre_clean_and_clean_slug
from web_api.services.ranking import run_live_ranking_for_slug


def _slug(campaign_id: int) -> str:
    return f"camp_{campaign_id}"


def _full_resumes_path(slug: str) -> Path:
    """Единый путь полных резюме для кампании (должен совпадать с fetch_full_resumes)."""
    return RAW_FULL_RESUMES / f"resumes_{slug}.json"


def _require_full_resumes(slug: str, expected_short: int) -> int:
    """Проверка после скачивания: файл есть и не пустой (защита от рассинхрона имён)."""
    path = _full_resumes_path(slug)
    if not path.exists():
        raise RuntimeError("RESUME_FILE_MISSING")
    data = load_json(path) or []
    if not isinstance(data, list) or len(data) == 0:
        raise RuntimeError("RESUME_DOWNLOAD_FAILED")
    if expected_short > 0 and len(data) < max(1, expected_short // 2):
        raise RuntimeError(
            f"RESUME_DOWNLOAD_PARTIAL: скачано {len(data)} из {expected_short}"
        )
    return len(data)


def _headers(token: str) -> dict:
    from services.api.hh_http import hh_headers

    return hh_headers(token)


def fetch_resume_short_list(token: str, search_text: str, pages: int) -> list:
    results = []
    for page in range(pages):
        params = {"text": search_text, "page": page, "per_page": 20}
        resp = requests.get(
            "https://api.hh.ru/resumes",
            headers=_headers(token),
            params=params,
            timeout=30,
        )
        if resp.status_code == 429:
            raise RuntimeError("Лимит API hh.ru (429). Подождите и повторите.")
        if resp.status_code != 200:
            raise RuntimeError(f"Ошибка поиска резюме на hh.ru (код {resp.status_code})")
        items = resp.json().get("items", [])
        if not items:
            break
        results.extend(items)
        time.sleep(0.4)
    return results


def _save_short_resumes(slug: str, search_text: str, items: list) -> Path:
    RAW_PART_RESUMES.mkdir(parents=True, exist_ok=True)
    path = RAW_PART_RESUMES / f"resumes_{slug}.json"
    for r in items:
        r["query"] = search_text
    save_json(path, items)
    return path


def _save_vacancy_full(slug: str, search_text: str, hh_raw: dict) -> None:
    RAW_FULL_VACANCIES.mkdir(parents=True, exist_ok=True)
    hh_raw = dict(hh_raw)
    hh_raw["query"] = search_text
    save_json(RAW_FULL_VACANCIES / f"vacancies_{slug}.json", [hh_raw])


def copy_demo_corpus(slug: str, search_text: str, fallback: str, hh_vacancy_raw: dict) -> int:
    """Копирует готовый корпус резюме для демо/скриншотов, если нет токена HH."""
    fb = fallback.replace(" ", "_")
    src_res = RAW_FULL_RESUMES / f"resumes_{fb}.json"
    if not src_res.exists():
        src_res = RAW_FULL_RESUMES / "resumes_full.json"
    if not src_res.exists():
        raise FileNotFoundError("Нет демо-данных для пробного режима без hh.ru")
    RAW_FULL_RESUMES.mkdir(parents=True, exist_ok=True)
    data = load_json(src_res) or []
    if isinstance(data, list):
        subset = data[:CAMPAIGN_MAX_FULL_RESUMES]
        for r in subset:
            r["query"] = search_text
        save_json(RAW_FULL_RESUMES / f"resumes_{slug}.json", subset)
    _save_vacancy_full(slug, search_text, hh_vacancy_raw)
    short = [{"id": r.get("id"), "title": r.get("title"), "query": search_text} for r in subset if r.get("id")]
    _save_short_resumes(slug, search_text, short)
    return len(subset)


def ingest_from_hh(
    campaign_id: int,
    hh_vacancy_id: str,
    search_text: str,
    hh_vacancy_raw: dict | None = None,
) -> dict:
    slug = _slug(campaign_id)
    token, token_err = resolve_hh_token()
    hh_raw = hh_vacancy_raw or fetch_vacancy_by_id(hh_vacancy_id)

    if token_err:
        raise RuntimeError(token_err)

    if not token:
        n = copy_demo_corpus(slug, search_text, CAMPAIGN_DEMO_FALLBACK_QUERY, hh_raw)
        stats = pre_clean_and_clean_slug(slug)
        return {"slug": slug, "demo_mode": True, "resumes_fetched": n, **stats}

    short = fetch_resume_short_list(token, search_text, CAMPAIGN_RESUME_SEARCH_PAGES)
    if not short:
        raise RuntimeError("По поисковому запросу не найдено резюме на hh.ru")

    short = short[: CAMPAIGN_MAX_FULL_RESUMES]
    n_short = len(short)
    _save_short_resumes(slug, search_text, short)
    _save_vacancy_full(slug, search_text, hh_raw)

    # file_key = slug — то же имя, что у краткого списка и у clean/rank
    fetch_full_resumes(token, short, slug)
    n_full = _require_full_resumes(slug, n_short)

    full_path = _full_resumes_path(slug)
    if n_full > CAMPAIGN_MAX_FULL_RESUMES:
        save_json(full_path, (load_json(full_path) or [])[:CAMPAIGN_MAX_FULL_RESUMES])

    stats = pre_clean_and_clean_slug(slug)
    return {"slug": slug, "demo_mode": False, "resumes_fetched": n_full, **stats}


def rank_campaign(campaign_id: int, vacancy_id: str) -> dict:
    slug = _slug(campaign_id)
    return run_live_ranking_for_slug(slug, vacancy_id)
