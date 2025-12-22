import json
import re
from pathlib import Path
from typing import List, Dict
from services.normalization.tech_aliases import TECH_ALIASES

PRE_CLEANED_DIR = Path("../data/prepared/resumes/pre-cleaned")
OUT_DIR_CLASSICAL = Path("../data/prepared/resumes/cleaned/classical")
OUT_DIR_TRANSFORMER = Path("../data/prepared/resumes/cleaned/transformer")
OUT_DIR_CLASSICAL.mkdir(parents=True, exist_ok=True)
OUT_DIR_TRANSFORMER.mkdir(parents=True, exist_ok=True)


# Для классических моделей
def normalize_for_classical(text: str) -> str:
    """Полная обработка для TF-IDF/BM25"""
    if not text:
        return ""
    text = text.lower()
    # Применяем TECH_ALIASES
    for pattern, repl in TECH_ALIASES.items():
        text = re.sub(pattern, repl, text)
    # Удаление специальных символов
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # TODO: Добавить лемматизацию здесь
    return text


# Для трансформеров
def normalize_for_transformer(text: str) -> str:
    """Минимальная обработка для трансформеров"""
    if not text:
        return ""
    text = text.strip()
    # Убираем лишние пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text)
    # Для skills применяем TECH_ALIASES
    text = normalize_tech_aliases(text)
    return text


def normalize_tech_aliases(text: str) -> str:
    """Применяем TECH_ALIASES к тексту"""
    for pattern, repl in TECH_ALIASES.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


# ---------- ПОЛЯ ДЛЯ КЛАССИЧЕСКИХ МОДЕЛЕЙ ----------
def build_title_classical(resume: dict) -> str:
    """Title для классических моделей"""
    title = resume.get("title", "")
    return normalize_for_classical(title)


def build_skills_classical(resume: dict) -> str:
    """Skills для классических моделей"""
    parts = []
    if resume.get("skills"):
        parts.append(resume["skills"])
    if resume.get("skill_set"):
        parts.extend(resume["skill_set"])
    skills_text = " ".join(parts)
    return normalize_for_classical(skills_text)


def build_experience_classical(resume: dict) -> str:
    """Experience для классических моделей"""
    parts = []
    for exp in resume.get("experience", []):
        if exp.get("description"):
            parts.append(exp["description"])
    experience_text = " ".join(parts)
    return normalize_for_classical(experience_text)


def build_positions_classical(resume: dict) -> List[str]:
    """Positions для классических моделей (список)"""
    positions = []
    for exp in resume.get("experience", []):
        if exp.get("position"):
            position_norm = normalize_for_classical(exp["position"])
            if position_norm:
                positions.append(position_norm)
    return list(set(positions))  # Уникальные позиции


# ---------- ПОЛЯ ДЛЯ ТРАНСФОРМЕРОВ ----------
def build_text_transformer(resume: dict) -> str:
    """Единый текст для трансформеров"""
    parts = []

    # Title
    title = resume.get("title", "")
    if title:
        parts.append(f"Должность: {title}")

    # Professional roles
    for role in resume.get("professional_roles", []):
        if role.get("name"):
            parts.append(f"Роль: {role['name']}")

    # Skills
    skills_parts = []
    if resume.get("skills"):
        skills_parts.append(resume["skills"])
    if resume.get("skill_set"):
        skills_parts.extend(resume["skill_set"])
    if skills_parts:
        skills_text = normalize_for_transformer(" ".join(skills_parts))
        parts.append(f"Навыки: {skills_text}")

    # Experience (только описания)
    experience_parts = []
    for exp in resume.get("experience", []):
        if exp.get("description"):
            exp_text = exp["description"]
            # Минимальная очистка для трансформеров
            exp_text = re.sub(r'\s+', ' ', exp_text).strip()
            experience_parts.append(exp_text)
    if experience_parts:
        experience_text = " ".join(experience_parts)
        parts.append(f"Опыт работы: {experience_text}")

    return " ".join(parts)


# ---------- META ----------
def build_meta(resume: dict) -> dict:
    """Метаданные для обоих форматов"""
    total_exp = resume.get("total_experience") or {}
    return {
        "id": resume.get("id"),
        "query": resume.get("query", ""),
        "total_experience_months": total_exp.get("months"),
        # Дополнительные метаданные если нужно
    }


# ---------- ОСНОВНАЯ ОБРАБОТКА ----------
def process_resume_classical(resume: dict) -> dict:
    """Обработка резюме для классических моделей"""
    result = build_meta(resume)

    # Основные поля
    result["title"] = build_title_classical(resume)
    result["skills"] = build_skills_classical(resume)
    result["experience"] = build_experience_classical(resume)
    result["positions"] = build_positions_classical(resume)

    return result


def process_resume_transformer(resume: dict) -> dict:
    """Обработка резюме для трансформеров"""
    result = build_meta(resume)

    # Единый текст
    result["text"] = build_text_transformer(resume)

    return result


# ---------- ОБРАБОТКА ФАЙЛОВ ----------
def process_files():
    for file_path in PRE_CLEANED_DIR.glob("resumes_*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Обрабатываем для классических моделей
        classical_data = []
        transformer_data = []

        for resume in data:
            classical_data.append(process_resume_classical(resume))
            transformer_data.append(process_resume_transformer(resume))

        # Сохраняем классические
        out_path_classical = OUT_DIR_CLASSICAL / file_path.name
        with open(out_path_classical, "w", encoding="utf-8") as f:
            json.dump(classical_data, f, ensure_ascii=False, indent=2)

        # Сохраняем трансформерные
        out_path_transformer = OUT_DIR_TRANSFORMER / file_path.name
        with open(out_path_transformer, "w", encoding="utf-8") as f:
            json.dump(transformer_data, f, ensure_ascii=False, indent=2)

        print(f"✅ {file_path.name}")
        print(f"   → Classical: {len(classical_data)} записей")
        print(f"   → Transformer: {len(transformer_data)} записей")
        print(f"   Example classical: {classical_data[0]['title'][:50]}...")
        print(f"   Example transformer text length: {len(transformer_data[0]['text'])} chars")


if __name__ == "__main__":
    process_files()