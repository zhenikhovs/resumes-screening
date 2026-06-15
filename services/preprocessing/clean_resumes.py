"""
Преобразование pre-cleaned резюме в форматы classical и transformer для ранжирования.
"""
import re
from typing import List
import pymorphy3

from config.paths import PRE_CLEANED_RESUMES, RESUMES_CLASSICAL, RESUMES_TRANSFORMER
from config.pipeline_config import (
    EMBEDDING_EXPERIENCE_JOBS,
    EMBEDDING_EXPERIENCE_MAX_CHARS,
    RERANK_EXPERIENCE_JOBS,
    RERANK_EXPERIENCE_MAX_CHARS,
)
from services.preprocessing.normalization.tech_aliases import TECH_ALIASES
from services.utils import safe_get, save_json, load_json

RESUMES_CLASSICAL.mkdir(parents=True, exist_ok=True)
RESUMES_TRANSFORMER.mkdir(parents=True, exist_ok=True)

morph = pymorphy3.MorphAnalyzer()
RUSSIAN_STOP_WORDS = {
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так',
    'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было',
    'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни'
}


def smart_lemmatize(text: str) -> str:
    if not text:
        return ""
    for pattern, replacement in TECH_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    words = re.findall(r'[a-zA-Zа-яёА-ЯЁ0-9._-]+', text)
    lemmas = []
    for word in words:
        word_lower = word.lower()
        if word_lower in RUSSIAN_STOP_WORDS:
            continue
        if re.match(r'^[а-яё]+$', word_lower):
            try:
                lemmas.append(morph.parse(word_lower)[0].normal_form)
            except Exception:
                lemmas.append(word_lower)
        else:
            lemmas.append(word_lower)
    return ' '.join(lemmas)


def normalize_for_classical(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', smart_lemmatize(text)).strip()


def normalize_for_transformer(text: str) -> str:
    if not text:
        return ""
    for pattern, replacement in TECH_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip()


def join_experience_descriptions(resume: dict) -> str:
    """Полная склейка experience[].description — для classical."""
    parts = [safe_get(exp, "description") for exp in safe_get(resume, "experience", [])]
    return " ".join(p for p in parts if p)


def join_recent_experience_descriptions(
    resume: dict,
    max_jobs: int,
    max_chars: int,
) -> str:
    """Усечённый опыт: первые max_jobs записей (как на hh — обычно от новых к старым), лимит символов."""
    parts: List[str] = []
    total = 0
    for exp in safe_get(resume, "experience", [])[:max_jobs]:
        desc = safe_get(exp, "description")
        if not desc:
            continue
        chunk = normalize_for_transformer(desc)
        if not chunk:
            continue
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining > 80:
                trimmed = chunk[:remaining].rsplit(" ", 1)[0]
                if trimmed:
                    parts.append(trimmed)
            break
        parts.append(chunk)
        total += len(chunk) + 1
    return " ".join(parts)


def build_title_classical(resume: dict) -> str:
    return normalize_for_classical(safe_get(resume, "title"))


def build_skills_classical(resume: dict) -> str:
    parts = []
    for skill in safe_get(resume, "skill_set", []):
        if isinstance(skill, str) and skill.strip():
            n = normalize_for_classical(skill)
            if n:
                parts.append(n)
    languages = []
    for lang in safe_get(resume, "language", []):
        name = safe_get(lang, "name")
        if name:
            level = safe_get(lang.get("level", {}), "name")
            languages.append(f"{name.lower()} ({level.lower()})" if level else name.lower())
    if languages:
        parts.append(" ".join(languages))
    return " ".join(parts)


def build_experience_classical(resume: dict) -> str:
    return normalize_for_classical(join_experience_descriptions(resume))


def ordered_unique_positions(resume: dict) -> List[str]:
    seen = set()
    out: List[str] = []
    for exp in safe_get(resume, "experience", []):
        pos = safe_get(exp, "position")
        if not pos:
            continue
        s = str(pos).strip()
        if not s:
            continue
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out


def build_positions_classical(resume: dict) -> List[str]:
    positions = set()
    for exp in safe_get(resume, "experience", []):
        pos = safe_get(exp, "position")
        if pos and normalize_for_classical(pos):
            positions.add(normalize_for_classical(pos))
    return list(positions)


def build_meta(resume: dict) -> dict:
    total_exp = safe_get(resume, "total_experience", {})
    return {"id": safe_get(resume, "id"), "query": safe_get(resume, "query"), "total_experience_months": safe_get(total_exp, "months")}


def resume_display_title(resume: dict) -> str:
    """Название резюме с hh (для UI); не используется в text для эмбеддингов."""
    title = safe_get(resume, "title")
    return str(title).strip() if title else ""


def _transformer_core_parts(resume: dict) -> List[str]:
    parts: List[str] = []
    if safe_get(resume, "title"):
        parts.append(f"Должность: {resume['title']}")
    skill_set = safe_get(resume, "skill_set", [])
    if skill_set:
        parts.append(f"Навыки: {', '.join(str(s) for s in skill_set)}")
    languages = []
    for lang in safe_get(resume, "language", []):
        name = safe_get(lang, "name")
        if name:
            level = safe_get(lang.get("level", {}), "name")
            languages.append(f"{name} ({level})" if level else name)
    if languages:
        parts.append(f"Языки: {', '.join(languages)}")
    return parts


def _transformer_text_with_experience(
    resume: dict,
    max_jobs: int,
    max_chars: int,
) -> str:
    parts = _transformer_core_parts(resume)
    positions = ordered_unique_positions(resume)
    if positions:
        parts.append(f"Позиции: {', '.join(positions)}")
    exp_text = join_recent_experience_descriptions(resume, max_jobs, max_chars)
    if exp_text:
        parts.append(f"Опыт: {exp_text}")
    return ". ".join(parts)


def process_resume_classical(resume: dict) -> dict:
    result = build_meta(resume)
    title = build_title_classical(resume)
    if not title or len(title) < 2:
        print(f"  ⚠️  Пустой title для resume {result['id']}")
    skills = build_skills_classical(resume)
    if not skills or len(skills) < 2:
        print(f"  ⚠️  Пустой skills для resume {result['id']}")
    result.update({
        "title": title,
        "skills": skills,
        "experience": build_experience_classical(resume),
        "positions": build_positions_classical(resume),
    })
    return result


def process_resume_transformer(resume: dict) -> dict:
    from services.preprocessing.resume_display import build_resume_summary

    result = build_meta(resume)
    display_title = resume_display_title(resume)
    if display_title:
        result["resume_title"] = display_title
    summary = build_resume_summary(resume)
    if summary:
        result["resume_summary"] = summary
    result["text"] = _transformer_text_with_experience(
        resume, EMBEDDING_EXPERIENCE_JOBS, EMBEDDING_EXPERIENCE_MAX_CHARS
    )
    result["text_rerank"] = _transformer_text_with_experience(
        resume, RERANK_EXPERIENCE_JOBS, RERANK_EXPERIENCE_MAX_CHARS
    )
    return result


def process_files():
    for file_path in sorted(PRE_CLEANED_RESUMES.glob("resumes_*.json")):
        print(f"\n📄 Обработка: {file_path.name}")
        data = load_json(file_path)
        if not data:
            print("  ❌ Файл пуст")
            continue
        classical_data = []
        transformer_data = []
        for resume in data:
            try:
                classical_data.append(process_resume_classical(resume))
                transformer_data.append(process_resume_transformer(resume))
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")
                continue
        save_json(RESUMES_CLASSICAL / file_path.name, classical_data)
        save_json(RESUMES_TRANSFORMER / file_path.name, transformer_data)
        print(f"  ✅ Обработано: {len(classical_data)} записей")


if __name__ == "__main__":
    process_files()
