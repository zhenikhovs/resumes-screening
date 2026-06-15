"""Удаление лишних полей из сырых полных резюме → pre-cleaned.

Вход: data/raw/full/resumes/ (только что полученные из HH полные резюме).
Выход: data/prepared/resumes/pre-cleaned/
"""
from config.paths import RAW_FULL_RESUMES, PRE_CLEANED_RESUMES
from services.utils import load_json, save_json

PRE_CLEANED_RESUMES.mkdir(parents=True, exist_ok=True)

FIELDS_TO_REMOVE = [
    "last_name", "first_name", "middle_name", "photo", "can_view_full_info",
    "negotiations_history", "actions", "alternate_url", "download", "owner",
    "real_id", "created_at", "updated_at", "certificate", "hidden_fields",
    "metro", "recommendation", "site", "favorited", "view_without_contacts_reason",
    "contact", "specialization", "tags", "district", "paid_services", "portfolio", "platform",
]


def clean_resume(resume: dict) -> dict:
    return {k: v for k, v in resume.items() if k not in FIELDS_TO_REMOVE}


def process_files():
    for file_path in sorted(RAW_FULL_RESUMES.glob("resumes_*.json")):
        data = load_json(file_path)
        if not isinstance(data, list):
            print(f"⚠ Файл {file_path.name} не содержит список резюме, пропускаем")
            continue
        cleaned_data = [clean_resume(r) for r in data]
        save_path = PRE_CLEANED_RESUMES / file_path.name
        save_json(save_path, cleaned_data)
        print(f"✅ {file_path.name} → {save_path.name} ({len(cleaned_data)} резюме)")


if __name__ == "__main__":
    process_files()
