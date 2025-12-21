import json
from pathlib import Path
from collections import defaultdict


# ===== Пути =====
PRE_CLEANED_DIR = Path("../data/prepared/resumes/pre-cleaned")
OUT_DIR = Path("../data/prepared/resumes/cleaned")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ===== Поля, которые оставляем в data =====
FIELDS_TO_KEEP = {
    "title",
    "area",
    "age",
    "gender",
    "salary",
    "total_experience",
    "employment_form",
    "work_format",
    "resume_locale",
    "skills",
    "citizenship",
    "work_ticket",
    "education",
    "employment",
    "employments",
    "experience",
    "language",
    "relocation",
    "schedule",
    "schedules",
    "travel_time",
    "business_trip_readiness",
    "skill_set",
    "has_vehicle",
    "driver_license_types",
    "professional_roles",
}


# ===== Очистка одного резюме =====
def clean_resume(resume: dict) -> dict:
    return {
        "meta": {
            "id": resume.get("id"),
            "query": resume.get("query"),
        },
        "data": {
            k: resume.get(k)
            for k in FIELDS_TO_KEEP
            if k in resume
        }
    }


# ===== Основная обработка =====
def process_files():
    grouped_by_query = defaultdict(list)

    for file_path in PRE_CLEANED_DIR.glob("resumes_*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print(f"⚠ Пропуск {file_path.name}: не список")
            continue

        for resume in data:
            cleaned = clean_resume(resume)

            query = cleaned["meta"]["query"] or "unknown"
            grouped_by_query[query].append(cleaned)

        print(f"✔ Прочитан {file_path.name} ({len(data)} резюме)")

    # ===== Сохранение =====
    for query, resumes in grouped_by_query.items():
        safe_query = query.replace(" ", "_").lower()
        out_path = OUT_DIR / f"resumes_{safe_query}.json"

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(resumes, f, ensure_ascii=False, indent=2)

        print(f"✅ Сохранено: {out_path.name} ({len(resumes)} резюме)")


if __name__ == "__main__":
    process_files()
