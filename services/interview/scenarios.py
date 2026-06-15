"""Загрузка сценариев интервью (вопросы + эталоны)."""
from pathlib import Path
from typing import Any

from config.interview_config import INTERVIEW_PASS_THRESHOLD
from config.paths import INTERVIEWS_SCENARIOS_DIR, VACANCIES_TRANSFORMER
from services.ranking.experience_text import append_experience_to_vacancy_text
from services.utils import load_json, save_json


def load_scenario(query: str) -> dict[str, Any]:
    path = INTERVIEWS_SCENARIOS_DIR / f"{query}.json"
    if not path.exists():
        raise FileNotFoundError(f"Сценарий не найден: {path}")
    data = load_json(path)
    if not isinstance(data, dict) or not data.get("questions"):
        raise ValueError(f"Некорректный сценарий (нет questions): {path}")
    out: dict[str, Any] = {
        "questions": data["questions"],
        "query": query,
        "pass_threshold": INTERVIEW_PASS_THRESHOLD,
    }
    if data.get("vacancy_text"):
        out["vacancy_text"] = data["vacancy_text"]
    return out


def get_question_by_id(scenario: dict, question_id: str) -> dict[str, Any]:
    for q in scenario.get("questions", []):
        if q.get("question_id") == question_id:
            return q
    raise KeyError(f"question_id={question_id} не найден в сценарии {scenario.get('query')}")


def resolve_vacancy_text(scenario: dict) -> str:
    if scenario.get("vacancy_text"):
        return str(scenario["vacancy_text"]).strip()

    query = scenario.get("query", "")
    vac_path = VACANCIES_TRANSFORMER / f"vacancies_{query}.json"
    vacancies = load_json(vac_path)
    if not vacancies:
        return f"(текст вакансии для query={query} не найден)"

    v = vacancies[0]
    text = v.get("text") or ""
    if text:
        return append_experience_to_vacancy_text(v)
    parts = [v.get("title", ""), v.get("skills", ""), v.get("requirements", "")]
    return " ".join(p for p in parts if p).strip() or f"(вакансия {query})"


def interview_dir(interview_id: str) -> Path:
    from config.paths import INTERVIEWS_DIR

    return INTERVIEWS_DIR / interview_id


def question_dir(interview_id: str, question_id: str) -> Path:
    return interview_dir(interview_id) / "questions" / question_id


def save_interview_meta(interview_id: str, meta: dict) -> Path:
    d = interview_dir(interview_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "meta.json"
    save_json(path, meta)
    return path


def load_interview_meta(interview_id: str) -> dict:
    path = interview_dir(interview_id) / "meta.json"
    data = load_json(path)
    if not isinstance(data, dict) or not data:
        raise FileNotFoundError(f"meta.json не найден для interview_id={interview_id}")
    return data
