"""Получение вакансии с hh.ru по URL."""
import re

import requests

from services.api.hh_http import hh_headers
from web_api.services.hh_token import resolve_hh_token

HH_VACANCY_URL = "https://api.hh.ru/vacancies/{vacancy_id}"


def parse_vacancy_id(hh_url: str) -> str:
    patterns = [
        r"hh\.ru/vacancy/(\d+)",
        r"hh\.ru/vacancies/(\d+)",
        r"vacancyId=(\d+)",
        r"^(\d+)$",
    ]
    for p in patterns:
        m = re.search(p, hh_url.strip())
        if m:
            return m.group(1)
    raise ValueError("Не удалось извлечь ID вакансии из URL")


def _parse_hh_error(resp: requests.Response) -> str:
    try:
        data = resp.json()
        desc = data.get("description", "")
        errs = data.get("errors") or []
        parts = [desc] if desc else []
        for e in errs:
            t = e.get("type", "")
            v = e.get("value", "")
            if t or v:
                parts.append(f"{t}: {v}")
        if parts:
            return "; ".join(parts)
    except Exception:
        pass
    return resp.text[:300] if resp.text else resp.reason


def fetch_vacancy_by_id(vacancy_id: str) -> dict:
    """
    GET /vacancies/{id}. Сначала без токена; при 403 — с токеном работодателя (архив/своя вакансия).
    """
    url = HH_VACANCY_URL.format(vacancy_id=vacancy_id)
    resp = requests.get(url, headers=hh_headers(), timeout=30)

    if resp.status_code == 200:
        return resp.json()

    if resp.status_code == 403:
        token, token_err = resolve_hh_token()
        if token_err:
            raise RuntimeError(
                f"Вакансия {vacancy_id} недоступна публично (403). {token_err}"
            ) from None
        if token:
            resp2 = requests.get(url, headers=hh_headers(token), timeout=30)
            if resp2.status_code == 200:
                return resp2.json()
            detail = _parse_hh_error(resp2)
            raise RuntimeError(
                f"Не удалось загрузить вакансию {vacancy_id} (HTTP {resp2.status_code}): {detail}"
            ) from None

    detail = _parse_hh_error(resp)
    if resp.status_code == 404:
        raise ValueError(
            f"Вакансия {vacancy_id} не найдена на hh.ru (снята или неверный ID)."
        )
    if "bad_user_agent" in detail.lower() or "user-agent" in detail.lower():
        raise RuntimeError(
            f"Отклонён User-Agent для API hh.ru: {detail}. "
            f"Задайте HH_CONTACT_EMAIL или WEB_HR_EMAIL в .env (формат: App/1.0 (email))."
        )
    raise RuntimeError(
        f"Не удалось загрузить вакансию {vacancy_id} (HTTP {resp.status_code}): {detail}"
    )
