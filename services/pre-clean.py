import json
from pathlib import Path

# Пути
RAW_DIR = Path("../data/raw/full/resumes")
CLEAN_DIR = Path("../data/prepared/resumes/pre-cleaned")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

# Поля, которые точно нужно удалить
FIELDS_TO_REMOVE = [
    "last_name",
    "first_name",
    "middle_name",
    "photo",
    "can_view_full_info",
    "negotiations_history",
    "actions",
    "alternate_url",
    "download",
    "owner",
    "real_id",
    "created_at",
    "updated_at",
    "certificate",
    "hidden_fields",
    "metro",
    "recommendation",
    "site",
    "favorited",
    "view_without_contacts_reason",
    "contact",
    "specialization",
    "tags",
    "district",
    "paid_services",
    "portfolio",
    "platform"
]


def clean_resume(resume: dict) -> dict:
    """Удаляет ненужные поля из одного резюме"""
    return {k: v for k, v in resume.items() if k not in FIELDS_TO_REMOVE}

def process_files():
    for file_path in RAW_DIR.glob("resumes_*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"⚠ Файл {file_path.name} не содержит список резюме, пропускаем")
                continue

        cleaned_data = [clean_resume(r) for r in data]

        save_path = CLEAN_DIR / file_path.name
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

        print(f"✅ {file_path.name} → {save_path.name} ({len(cleaned_data)} резюме)")

if __name__ == "__main__":
    process_files()
