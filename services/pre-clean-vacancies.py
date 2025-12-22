import json
from pathlib import Path
from bs4 import BeautifulSoup

# Пути
RAW_DIR = Path("../data/raw/full/vacancies")
CLEAN_DIR = Path("../data/prepared/vacancies/pre-cleaned")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

# Поля, которые точно удаляем
FIELDS_TO_REMOVE = [
    "premium", "billing_type", "can_upgrade_billing_type",
    "relations", "insider_interview", "response_letter_required",
    "department", "show_contacts", "contacts",
    "branded_description", "vacancy_constructor_template",
    "auto_response", "accept_handicapped", "accept_kids", "age_restriction",
    "archived", "response_url", "adv_response_url",
    "code", "hidden", "quick_responses_allowed", "driver_license_types", "accept_incomplete_resumes",
    "negotiations_url", "suitable_resumes_url", "apply_alternate_url", "alternate_url", "has_test", "test",
    "show_logo_in_search", "closed_for_applicants",
    "fly_in_fly_out_duration", "internship", "night_shifts",
    "type", "published_at", "created_at", "initial_created_at",
    "allow_messages", "employer", "area",
]

def clean_description(html_text):
    """Удаляет HTML из описания вакансии"""
    if not html_text:
        return ""
    return BeautifulSoup(html_text, "html.parser").get_text(separator="\n").strip()

def clean_vacancy(vacancy: dict) -> dict:
    """Удаляет лишние поля и оставляет только нужное"""
    cleaned = {k: v for k, v in vacancy.items() if k not in FIELDS_TO_REMOVE}

    # Оставляем только city, lat, lng из address
    if "address" in vacancy and isinstance(vacancy["address"], dict):
        cleaned["address"] = {
            "city": vacancy["address"].get("city"),
        }

    # Чистим описание
    if "description" in vacancy:
        cleaned["description"] = clean_description(vacancy["description"])

    # Преобразуем списки skills, languages, work_format, work_schedule_by_days, working_hours
    for field in ["key_skills", "languages", "work_format", "work_schedule_by_days", "working_hours"]:
        if field in vacancy and isinstance(vacancy[field], list):
            cleaned[field] = [item.get("name") if isinstance(item, dict) else item for item in vacancy[field]]

    # Преобразуем employment, experience, schedule
    for field in ["employment", "experience", "schedule"]:
        if field in vacancy and isinstance(vacancy[field], dict):
            cleaned[field] = vacancy[field].get("name")

    # Чистим employer
    if "employer" in vacancy and isinstance(vacancy["employer"], dict):
        cleaned["employer"] = {
            "id": vacancy["employer"].get("id"),
            "name": vacancy["employer"].get("name")
        }

    return cleaned

def process_files():
    for file_path in RAW_DIR.glob("vacancies_*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"⚠ Файл {file_path.name} не содержит список вакансий, пропускаем")
                continue

        cleaned_data = [clean_vacancy(v) for v in data]

        save_path = CLEAN_DIR / file_path.name
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        print(f"✅ {file_path.name} → {save_path.name} ({len(cleaned_data)} вакансий)")

if __name__ == "__main__":
    process_files()
