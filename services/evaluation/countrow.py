"""Подсчёт строк в JSON-файлах по директориям данных."""
from pathlib import Path
from config.paths import (
    RAW_FULL_RESUMES, RAW_FULL_VACANCIES,
    PRE_CLEANED_RESUMES, PRE_CLEANED_VACANCIES,
    RESUMES_CLASSICAL, RESUMES_TRANSFORMER,
    VACANCIES_CLASSICAL, VACANCIES_TRANSFORMER,
)

PATHS = [
    RAW_FULL_RESUMES, RAW_FULL_VACANCIES,
    PRE_CLEANED_RESUMES, PRE_CLEANED_VACANCIES,
    RESUMES_CLASSICAL, RESUMES_TRANSFORMER,
    VACANCIES_CLASSICAL, VACANCIES_TRANSFORMER,
]

for p in PATHS:
    if not p.exists():
        print(f"❌ Не найдена: {p}")
        continue
    total = 0
    print(f"\n📂 {p}")
    for f in sorted(p.glob("*.json")):
        try:
            lines = sum(1 for _ in open(f, "r", encoding="utf-8"))
            total += lines
            print(f"  {f.name}: {lines} строк")
        except Exception as e:
            print(f"⚠ {f.name}: {e}")
    print(f"  ➤ Всего: {total}")
