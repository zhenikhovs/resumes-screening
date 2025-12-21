import json
import os
from collections import Counter, defaultdict

VACANCIES_DIR = "../../data/raw/full/vacancies"

total_vacancies = 0
field_counter = Counter()
filled_fields = defaultdict(int)
files_stats = {}

vacancies_all = []

for file_name in os.listdir(VACANCIES_DIR):
    if not file_name.endswith(".json"):
        continue

    path = os.path.join(VACANCIES_DIR, file_name)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    files_stats[file_name] = len(data)
    total_vacancies += len(data)
    vacancies_all.extend(data)

    for vac in data:
        for field, value in vac.items():
            field_counter[field] += 1
            if value not in (None, "", [], {}):
                filled_fields[field] += 1

print(f"\nВсего вакансий: {total_vacancies}")

print("\n📂 Распределение по файлам:")
for k, v in files_stats.items():
    print(f"{k}: {v}")

print("\n📌 Поля верхнего уровня (кол-во вакансий, где встречается поле):")
for field, count in field_counter.most_common():
    print(f"{field}: {count}")

print("\n📌 Заполненность ключевых текстовых полей:")
key_fields = [
    "name",
    "description",
    "key_skills",
    "responsibility",
    "requirements",
    "experience",
    "professional_roles"
]

for field in key_fields:
    count = filled_fields.get(field, 0)
    percent = count / total_vacancies * 100 if total_vacancies else 0
    print(f"{field}: заполнено {count} ({percent:.1f}%)")
