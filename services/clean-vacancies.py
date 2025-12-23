import json
import re
from pathlib import Path
from typing import List, Dict
from services.normalization.tech_aliases import TECH_ALIASES

PRE_CLEANED_DIR = Path("../data/prepared/vacancies/pre-cleaned")
OUT_DIR_CLASSICAL = Path("../data/prepared/vacancies/cleaned/classical")
OUT_DIR_TRANSFORMER = Path("../data/prepared/vacancies/cleaned/transformer")
OUT_DIR_CLASSICAL.mkdir(parents=True, exist_ok=True)
OUT_DIR_TRANSFORMER.mkdir(parents=True, exist_ok=True)


def safe_get(data, key, default=""):
    """Безопасное получение значения"""
    value = data.get(key)
    return value if value is not None else default


def extract_key_skills(vacancy: dict) -> List[str]:
    """Извлечение ключевых навыков из вакансии"""
    skills = []
    key_skills = safe_get(vacancy, "key_skills", [])

    for skill in key_skills:
        if isinstance(skill, dict):
            # Если skill это объект {"name": "MongoDB"}
            skill_name = safe_get(skill, "name")
            if skill_name:
                skills.append(str(skill_name))
        elif isinstance(skill, str):
            # Если skill это строка "MongoDB"
            skills.append(skill)

    return skills


def parse_experience_text(exp_text: str) -> dict:
    """Парсинг текста опыта работы в месяцы"""
    """
    Примеры:
    - "Более 6 лет" → min: 72, max: None
    - "От 1 года до 3 лет" → min: 12, max: 36
    - "От 3 до 6 лет" → min: 36, max: 72
    - "Нет опыта" → min: 0, max: None
    """
    if not exp_text:
        return {"min": None, "max": None}

    exp_text = exp_text.lower()

    # 1. "Более X лет"
    match = re.search(r'более\s*(\d+)\s*лет', exp_text)
    if match:
        years = int(match.group(1))
        return {"min": years * 12, "max": None}

    # 2. "От X до Y лет"
    match = re.search(r'от\s*(\d+)\s*до\s*(\d+)\s*лет', exp_text)
    if match:
        min_years = int(match.group(1))
        max_years = int(match.group(2))
        return {"min": min_years * 12, "max": max_years * 12}

    # 3. "X лет" (точно)
    match = re.search(r'(\d+)\s*лет', exp_text)
    if match:
        years = int(match.group(1))
        return {"min": years * 12, "max": years * 12}

    # 4. "Нет опыта" или "Без опыта"
    if "нет" in exp_text or "без" in exp_text:
        return {"min": 0, "max": None}

    # По умолчанию
    return {"min": None, "max": None}


def normalize_for_classical(text: str) -> str:
    """Нормализация для классических моделей"""
    if not text:
        return ""

    # Применяем TECH_ALIASES
    for pattern, replacement in TECH_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Базовая очистка
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def normalize_for_transformer(text: str) -> str:
    """Нормализация для трансформеров"""
    if not text:
        return ""

    for pattern, replacement in TECH_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_requirements_from_description(description: str) -> str:
    """Извлечение требований из описания вакансии"""
    if not description:
        return ""

    lines = description.split('\n')
    requirements = []
    in_requirements_section = False

    # Ключевые слова для начала секции требований
    requirement_keywords = [
        'требования', 'ожидаем', 'нужно', 'должен',
        'желательно', 'обязательно', 'требуется'
    ]

    for line in lines:
        line_lower = line.lower().strip()

        # Начало секции требований
        if any(keyword in line_lower for keyword in requirement_keywords):
            in_requirements_section = True
            continue

        # Если мы в секции требований и строка не пустая
        if in_requirements_section and line.strip():
            # Останавливаемся, если начинается новая секция
            if line_lower.startswith(('что предлагаем', 'условия', 'задачи', 'обязанности')):
                break
            requirements.append(line.strip())

    # Если не нашли секцию требований, берем весь текст
    if not requirements:
        return description

    return " ".join(requirements)


def build_vacancy_classical(vacancy: dict) -> dict:
    """Создание структуры для классических моделей"""

    # Title
    title = safe_get(vacancy, "name", "")
    title_norm = normalize_for_classical(title)

    # Skills (key_skills)
    skills_list = extract_key_skills(vacancy)
    skills_text = " ".join(skills_list)
    skills_norm = normalize_for_classical(skills_text)

    # Requirements (из description)
    description = safe_get(vacancy, "description", "")
    requirements = extract_requirements_from_description(description)
    requirements_norm = normalize_for_classical(requirements)

    # Experience
    exp_text = safe_get(vacancy, "experience", "")
    exp_parsed = parse_experience_text(exp_text)

    return {
        "id": safe_get(vacancy, "id"),
        "query": safe_get(vacancy, "query", ""),
        "title": title_norm,
        "skills": skills_norm,
        "requirements": requirements_norm,
        "experience_text": exp_text,
        "min_experience_months": exp_parsed["min"],
        "max_experience_months": exp_parsed["max"]
    }


def build_vacancy_transformer(vacancy: dict) -> dict:
    """Создание структуры для трансформеров"""

    parts = []

    # Title
    title = safe_get(vacancy, "name", "")
    if title:
        parts.append(f"Должность: {title}")

    # Skills
    skills_list = extract_key_skills(vacancy)
    if skills_list:
        skills_text = ", ".join(skills_list)
        skills_text = normalize_for_transformer(skills_text)
        parts.append(f"Ключевые навыки: {skills_text}")

    # Requirements
    description = safe_get(vacancy, "description", "")
    requirements = extract_requirements_from_description(description)
    if requirements:
        parts.append(f"Требования: {requirements[:500]}...")  # Ограничиваем длину

    # Experience
    exp_text = safe_get(vacancy, "experience", "")
    if exp_text:
        parts.append(f"Требуемый опыт: {exp_text}")

    exp_parsed = parse_experience_text(exp_text)

    return {
        "id": safe_get(vacancy, "id"),
        "query": safe_get(vacancy, "query", ""),
        "text": ". ".join(parts),
        "min_experience_months": exp_parsed["min"],
        "max_experience_months": exp_parsed["max"]
    }


def process_vacancy_files():
    """Обработка всех файлов с вакансиями"""

    # Находим все файлы с вакансиями
    vacancy_files = list(PRE_CLEANED_DIR.glob("vacancies_*.json"))

    if not vacancy_files:
        print(f"❌ Файлы не найдены в {PRE_CLEANED_DIR}")
        print("Ожидаются файлы: vacancies_backend_developer.json, vacancies_project_manager.json и т.д.")
        return

    for file_path in vacancy_files:
        print(f"\n📄 Обработка вакансий: {file_path.name}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ❌ Ошибка чтения файла: {e}")
            continue

        if not data:
            print("  ❌ Файл пуст")
            continue

        classical_data = []
        transformer_data = []

        for vacancy in data:
            try:
                classical_vacancy = build_vacancy_classical(vacancy)
                transformer_vacancy = build_vacancy_transformer(vacancy)

                classical_data.append(classical_vacancy)
                transformer_data.append(transformer_vacancy)
            except Exception as e:
                print(f"  ⚠️  Ошибка обработки вакансии {vacancy.get('id', 'unknown')}: {e}")
                continue

        # Сохраняем классические вакансии
        out_classical = OUT_DIR_CLASSICAL / file_path.name
        with open(out_classical, "w", encoding="utf-8") as f:
            json.dump(classical_data, f, ensure_ascii=False, indent=2)

        # Сохраняем трансформерные вакансии
        out_transformer = OUT_DIR_TRANSFORMER / file_path.name
        with open(out_transformer, "w", encoding="utf-8") as f:
            json.dump(transformer_data, f, ensure_ascii=False, indent=2)

        print(f"  ✅ Обработано: {len(classical_data)} вакансий")

        # Показываем пример
        if classical_data:
            first = classical_data[0]
            print(f"  📋 Пример вакансии:")
            print(f"    Title: {first.get('title', '')[:50]}...")
            print(f"    Skills: {len(first.get('skills', ''))} символов")
            print(f"    Experience: {first.get('experience_text', '')}")


def main():
    print("🚀 ЗАПУСК ОБРАБОТКИ ВАКАНСИЙ")
    print("=" * 50)

    # Проверяем существование директории
    if not PRE_CLEANED_DIR.exists():
        print(f"❌ Директория не найдена: {PRE_CLEANED_DIR}")
        print("Создайте директорию и поместите туда файлы с вакансиями:")
        print("  data/prepared/vacancies/pre-cleaned/vacancies_backend_developer.json")
        print("  data/prepared/vacancies/pre-cleaned/vacancies_project_manager.json")
        return

    process_vacancy_files()

    print("\n" + "=" * 50)
    print("✅ ОБРАБОТКА ВАКАНСИЙ ЗАВЕРШЕНА")
    print(f"📁 Classical: {OUT_DIR_CLASSICAL}")
    print(f"📁 Transformer: {OUT_DIR_TRANSFORMER}")


if __name__ == "__main__":
    main()