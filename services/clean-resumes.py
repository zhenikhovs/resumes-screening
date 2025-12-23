import json
import re
from pathlib import Path
from typing import List, Dict
import pymorphy3

# Ваш TECH_ALIASES импорт
from services.normalization.tech_aliases import TECH_ALIASES

PRE_CLEANED_DIR = Path("../data/prepared/resumes/pre-cleaned")
OUT_DIR_CLASSICAL = Path("../data/prepared/resumes/cleaned/classical")
OUT_DIR_TRANSFORMER = Path("../data/prepared/resumes/cleaned/transformer")
OUT_DIR_CLASSICAL.mkdir(parents=True, exist_ok=True)
OUT_DIR_TRANSFORMER.mkdir(parents=True, exist_ok=True)

# Инициализация
morph = pymorphy3.MorphAnalyzer()

# Стоп-слова
RUSSIAN_STOP_WORDS = {
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как',
    'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к',
    'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было',
    'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь',
    'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни'
}


# Функция для безопасного получения данных
def safe_get(data, key, default=""):
    value = data.get(key)
    return value if value is not None else default


# ИСПРАВЛЕННАЯ лемматизация
def smart_lemmatize(text: str) -> str:
    """Умная лемматизация с сохранением тех. терминов"""
    if not text:
        return ""

    # 1. Сначала применяем TECH_ALIASES
    for pattern, replacement in TECH_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # 2. Разделяем на слова с сохранением технических терминов
    # Паттерн: слова (рус/англ), цифры, точка, дефис
    words = re.findall(r'[a-zA-Zа-яёА-ЯЁ0-9._-]+', text)

    lemmas = []
    for word in words:
        word_lower = word.lower()

        # Пропускаем стоп-слова
        if word_lower in RUSSIAN_STOP_WORDS:
            continue

        # Проверяем, русское ли слово
        if re.match(r'^[а-яё]+$', word_lower):
            try:
                parsed = morph.parse(word_lower)[0]
                lemma = parsed.normal_form
                lemmas.append(lemma)
            except:
                lemmas.append(word_lower)
        else:
            # Английские слова, цифры, тех. термины оставляем как есть
            lemmas.append(word_lower)

    return ' '.join(lemmas)


# Нормализация для классических моделей
def normalize_for_classical(text: str) -> str:
    """Полная обработка для классических моделей"""
    if not text:
        return ""

    # 1. Применяем TECH_ALIASES уже в smart_lemmatize
    # 2. Лемматизируем
    lemmatized = smart_lemmatize(text)

    # 3. Убираем лишние пробелы
    result = re.sub(r'\s+', ' ', lemmatized).strip()

    return result


# Нормализация для трансформеров
def normalize_for_transformer(text: str) -> str:
    """Минимальная обработка для трансформеров"""
    if not text:
        return ""

    # Только TECH_ALIASES и очистка
    for pattern, replacement in TECH_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ---------- ИСПРАВЛЕННЫЕ ФУНКЦИИ ----------
def build_title_classical(resume: dict) -> str:
    title = safe_get(resume, "title")
    return normalize_for_classical(title)


def build_skills_classical(resume: dict) -> str:
    """Skills ТОЛЬКО технические навыки и языки"""
    parts = []

    # ТОЛЬКО skill_set (список)
    skill_set = safe_get(resume, "skill_set", [])
    for skill in skill_set:
        if isinstance(skill, str) and skill.strip():
            # Применяем TECH_ALIASES к каждому навыку
            normalized = normalize_for_classical(skill)
            if normalized:
                parts.append(normalized)

    # Языки
    languages = []
    for lang in safe_get(resume, "language", []):
        name = safe_get(lang, "name")
        if name:
            level = safe_get(lang.get("level", {}), "name")
            lang_text = name.lower()
            if level:
                lang_text += f" ({level.lower()})"
            languages.append(lang_text)

    if languages:
        parts.append(" ".join(languages))

    return " ".join(parts)


def build_experience_classical(resume: dict) -> str:
    """ТОЛЬКО описания опыта работы (без должностей)"""
    parts = []
    for exp in safe_get(resume, "experience", []):
        description = safe_get(exp, "description")
        if description:
            parts.append(description)

    experience_text = " ".join(parts)
    return normalize_for_classical(experience_text)


def build_positions_classical(resume: dict) -> List[str]:
    """ТОЛЬКО названия должностей"""
    positions = set()  # Уникальные должности
    for exp in safe_get(resume, "experience", []):
        position = safe_get(exp, "position")
        if position:
            normalized = normalize_for_classical(position)
            if normalized:
                positions.add(normalized)

    return list(positions)


# ---------- META ----------
def build_meta(resume: dict) -> dict:
    total_exp = safe_get(resume, "total_experience", {})
    return {
        "id": safe_get(resume, "id"),
        "query": safe_get(resume, "query"),
        "total_experience_months": safe_get(total_exp, "months"),
    }


# ---------- ОСНОВНАЯ ОБРАБОТКА ----------
def process_resume_classical(resume: dict) -> dict:
    result = build_meta(resume)

    # КРИТИЧЕСКИ: проверяем каждое поле
    title = build_title_classical(resume)
    if not title or len(title) < 2:
        print(f"  ⚠️  Пустой title для resume {result['id']}")

    skills = build_skills_classical(resume)
    if not skills or len(skills) < 2:
        print(f"  ⚠️  Пустой skills для resume {result['id']}")

    experience = build_experience_classical(resume)
    positions = build_positions_classical(resume)

    result.update({
        "title": title,
        "skills": skills,
        "experience": experience,
        "positions": positions
    })

    return result


def process_resume_transformer(resume: dict) -> dict:
    """Для трансформеров - минимальная обработка"""
    result = build_meta(resume)

    # Собираем текст для трансформеров
    text_parts = []

    title = safe_get(resume, "title")
    if title:
        text_parts.append(f"Должность: {title}")

    # Skills из skill_set
    skill_set = safe_get(resume, "skill_set", [])
    if skill_set:
        skills_text = ", ".join([str(s) for s in skill_set])
        text_parts.append(f"Навыки: {skills_text}")

    # Языки
    languages = []
    for lang in safe_get(resume, "language", []):
        name = safe_get(lang, "name")
        if name:
            level = safe_get(lang.get("level", {}), "name")
            lang_text = name
            if level:
                lang_text += f" ({level})"
            languages.append(lang_text)

    if languages:
        text_parts.append(f"Языки: {', '.join(languages)}")

    # Experience (первые 3 места работы)
    exp_parts = []
    for exp in safe_get(resume, "experience", [])[:3]:  # Только первые 3
        position = safe_get(exp, "position")
        if position:
            exp_parts.append(f"{position}")

    if exp_parts:
        text_parts.append(f"Опыт: {', '.join(exp_parts)}")

    result["text"] = ". ".join(text_parts)
    return result


# ---------- ОБРАБОТКА ВСЕХ ФАЙЛОВ ----------
def process_files():
    for file_path in PRE_CLEANED_DIR.glob("resumes_*.json"):
        print(f"\n📄 Обработка: {file_path.name}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            print("  ❌ Файл пуст")
            continue

        classical_data = []
        transformer_data = []

        # ОБРАБАТЫВАЕМ ВСЕ РЕЗЮМЕ (без [:3])
        for resume in data:
            try:
                classical = process_resume_classical(resume)
                transformer = process_resume_transformer(resume)

                classical_data.append(classical)
                transformer_data.append(transformer)
            except Exception as e:
                print(f"  ❌ Ошибка обработки резюме: {e}")
                continue

        # Сохраняем
        out_classical = OUT_DIR_CLASSICAL / file_path.name
        out_transformer = OUT_DIR_TRANSFORMER / file_path.name

        with open(out_classical, "w", encoding="utf-8") as f:
            json.dump(classical_data, f, ensure_ascii=False, indent=2)

        with open(out_transformer, "w", encoding="utf-8") as f:
            json.dump(transformer_data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ Обработано: {len(classical_data)} записей")

        # Показываем пример первого резюме
        if classical_data:
            first = classical_data[0]
            print(f"  📋 Пример:")
            print(f"    Title: {first.get('title', '')[:50]}...")
            print(f"    Skills длина: {len(first.get('skills', ''))} символов")
            print(f"    Positions: {len(first.get('positions', []))} шт")


if __name__ == "__main__":
    print("🚀 Запуск исправленной обработки...")
    process_files()
    print("\n✅ Обработка завершена!")