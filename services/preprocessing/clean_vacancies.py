"""
Преобразование pre-cleaned вакансий в форматы classical и transformer для ранжирования.
"""
import re
from typing import List
from config.paths import PRE_CLEANED_VACANCIES, VACANCIES_CLASSICAL, VACANCIES_TRANSFORMER
from services.preprocessing.normalization.tech_aliases import TECH_ALIASES
from services.utils import safe_get, save_json, load_json

VACANCIES_CLASSICAL.mkdir(parents=True, exist_ok=True)
VACANCIES_TRANSFORMER.mkdir(parents=True, exist_ok=True)


def extract_key_skills(vacancy: dict) -> List[str]:
    skills = []
    for skill in safe_get(vacancy, "key_skills", []):
        if isinstance(skill, dict):
            if safe_get(skill, "name"):
                skills.append(str(skill["name"]))
        elif isinstance(skill, str):
            skills.append(skill)
    return skills


def parse_experience_text(exp_text: str) -> dict:
    if not exp_text:
        return {"min": None, "max": None}
    exp_text = exp_text.lower()
    m = re.search(r'более\s*(\d+)\s*лет', exp_text)
    if m:
        return {"min": int(m.group(1)) * 12, "max": None}
    m = re.search(r'от\s*(\d+)\s*до\s*(\d+)\s*лет', exp_text)
    if m:
        return {"min": int(m.group(1)) * 12, "max": int(m.group(2)) * 12}
    m = re.search(r'(\d+)\s*лет', exp_text)
    if m:
        y = int(m.group(1)) * 12
        return {"min": y, "max": y}
    if "нет" in exp_text or "без" in exp_text:
        return {"min": 0, "max": None}
    return {"min": None, "max": None}


def normalize_for_classical(text: str) -> str:
    if not text:
        return ""
    for pattern, replacement in TECH_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def normalize_for_transformer(text: str) -> str:
    if not text:
        return ""
    for pattern, replacement in TECH_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip()


def extract_requirements_from_description(description: str) -> str:
    if not description:
        return ""
    lines = description.split('\n')
    requirements = []
    in_requirements = False
    keywords = ['требования', 'ожидаем', 'нужно', 'должен', 'желательно', 'обязательно', 'требуется']
    for line in lines:
        low = line.lower().strip()
        if any(k in low for k in keywords):
            in_requirements = True
            continue
        if in_requirements and line.strip():
            if low.startswith(('что предлагаем', 'условия', 'задачи', 'обязанности')):
                break
            requirements.append(line.strip())
    return " ".join(requirements) if requirements else description


def build_vacancy_classical(vacancy: dict) -> dict:
    title = safe_get(vacancy, "name", "")
    skills_text = " ".join(extract_key_skills(vacancy))
    desc = safe_get(vacancy, "description", "")
    req = extract_requirements_from_description(desc)
    exp_text = safe_get(vacancy, "experience", "")
    exp_parsed = parse_experience_text(exp_text)
    return {
        "id": safe_get(vacancy, "id"),
        "query": safe_get(vacancy, "query", ""),
        "title": normalize_for_classical(title),
        "skills": normalize_for_classical(skills_text),
        "requirements": normalize_for_classical(req),
        "experience_text": exp_text,
        "min_experience_months": exp_parsed["min"],
        "max_experience_months": exp_parsed["max"],
    }


def build_vacancy_transformer(vacancy: dict) -> dict:
    parts = []
    if safe_get(vacancy, "name"):
        parts.append(f"Должность: {vacancy['name']}")
    skills_list = extract_key_skills(vacancy)
    if skills_list:
        parts.append(f"Ключевые навыки: {normalize_for_transformer(', '.join(skills_list))}")
    req = extract_requirements_from_description(safe_get(vacancy, "description", ""))
    if req:
        req_clean = normalize_for_transformer(req)
        if req_clean:
            parts.append(f"Требования: {req_clean}")
    if safe_get(vacancy, "experience"):
        parts.append(f"Требуемый опыт: {vacancy['experience']}")
    exp_parsed = parse_experience_text(safe_get(vacancy, "experience", ""))
    return {
        "id": safe_get(vacancy, "id"),
        "query": safe_get(vacancy, "query", ""),
        "text": ". ".join(parts),
        "min_experience_months": exp_parsed["min"],
        "max_experience_months": exp_parsed["max"],
    }


def process_vacancy_files():
    files = list(PRE_CLEANED_VACANCIES.glob("vacancies_*.json"))
    if not files:
        print(f"❌ Файлы не найдены в {PRE_CLEANED_VACANCIES}")
        return
    for file_path in sorted(files):
        print(f"\n📄 Обработка: {file_path.name}")
        data = load_json(file_path)
        if not data:
            print("  ❌ Файл пуст")
            continue
        classical_data = []
        transformer_data = []
        for vacancy in data:
            try:
                classical_data.append(build_vacancy_classical(vacancy))
                transformer_data.append(build_vacancy_transformer(vacancy))
            except Exception as e:
                print(f"  ⚠️  Ошибка вакансии {vacancy.get('id')}: {e}")
                continue
        save_json(VACANCIES_CLASSICAL / file_path.name, classical_data)
        save_json(VACANCIES_TRANSFORMER / file_path.name, transformer_data)
        print(f"  ✅ Обработано: {len(classical_data)} вакансий")


def main():
    if not PRE_CLEANED_VACANCIES.exists():
        print(f"❌ Директория не найдена: {PRE_CLEANED_VACANCIES}")
        return
    process_vacancy_files()
    print("\n✅ Обработка вакансий завершена")


if __name__ == "__main__":
    main()
