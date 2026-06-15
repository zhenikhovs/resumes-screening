"""Подписи резюме для UI (должность и краткое описание); не влияют на text для ML."""
from __future__ import annotations

from config.paths import RESUMES_TRANSFORMER
from services.utils import load_json

SUMMARY_MAX_LEN = 320


def position_from_record(record: dict) -> str:
    explicit = (record.get("resume_title") or "").strip()
    if explicit:
        return explicit
    return position_from_text(record.get("text") or "")


def position_from_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("Должность:", "", 1).strip()
    if ". Навыки:" in t:
        return t.split(". Навыки:")[0].strip()
    if "\n" in text:
        return text.split("\n")[0].replace("Должность:", "").strip()
    return t.split(". ")[0].strip() if ". " in t else t


def summary_from_record(record: dict) -> str:
    explicit = (record.get("resume_summary") or "").strip()
    if explicit:
        return _truncate(explicit)
    return summary_from_text(record.get("text") or "")


def summary_from_text(text: str) -> str:
    """Всё из text кроме блока «Должность: …» (навыки, языки, позиции, опыт)."""
    if not text:
        return ""
    t = text.strip()
    if t.startswith("Должность:"):
        dot = t.find(". ")
        if dot == -1:
            return ""
        t = t[dot + 2 :].strip()
    return _truncate(t)


def _truncate(s: str) -> str:
    s = s.strip()
    if len(s) <= SUMMARY_MAX_LEN:
        return s
    return s[: SUMMARY_MAX_LEN - 1].rstrip() + "…"


def build_resume_summary(resume: dict) -> str:
    """Краткое описание при clean (навыки + позиции с hh)."""
    from services.preprocessing.clean_resumes import ordered_unique_positions, safe_get

    parts: list[str] = []
    skill_set = safe_get(resume, "skill_set", [])
    if skill_set:
        skills = ", ".join(str(s) for s in skill_set[:35])
        parts.append(f"Навыки: {skills}")
    positions = ordered_unique_positions(resume)
    if positions:
        parts.append(f"Позиции: {', '.join(positions[:10])}")
    if not parts:
        return ""
    return _truncate(". ".join(parts))


def resume_display_map(query: str) -> dict[str, dict[str, str]]:
    path = RESUMES_TRANSFORMER / f"resumes_{query}.json"
    resumes = load_json(path) or []
    out: dict[str, dict[str, str]] = {}
    for r in resumes:
        rid = str(r.get("id", ""))
        if not rid:
            continue
        pos = position_from_record(r)
        summ = summary_from_record(r)
        out[rid] = {
            "position": pos or rid,
            "summary": summ,
        }
    return out


def display_for_resume_id(query: str, resume_id: str, fallback_title: str | None = None) -> dict[str, str]:
    mapped = resume_display_map(query).get(str(resume_id))
    if mapped:
        return mapped
    fb = (fallback_title or "").strip()
    if not fb:
        return {"position": str(resume_id), "summary": ""}
    if ". Навыки:" in fb:
        pos, _, rest = fb.partition(". Навыки:")
        pos = pos.replace("Должность:", "").strip() or str(resume_id)
        summary = _truncate("Навыки: " + rest.strip()) if rest.strip() else ""
        return {"position": pos, "summary": summary}
    if fb.startswith("Должность:"):
        return {
            "position": position_from_text(fb),
            "summary": summary_from_text(fb),
        }
    return {"position": fb[:120], "summary": ""}
