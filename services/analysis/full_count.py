import json
from pathlib import Path
from collections import defaultdict

RESUMES_DIR = Path("../../data/raw/full/resumes")


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if not RESUMES_DIR.exists():
        raise FileNotFoundError(f"Директория не найдена: {RESUMES_DIR}")

    total_records = 0
    all_ids = []
    per_query_count = {}

    for file_path in RESUMES_DIR.glob("resumes_*.json"):
        data = load_json(file_path)

        if not isinstance(data, list):
            print(f"⚠ Пропущен файл (не список): {file_path.name}")
            continue

        count = len(data)
        per_query_count[file_path.name] = count
        total_records += count

        for r in data:
            if "id" in r:
                all_ids.append(r["id"])

    unique_ids = set(all_ids)

    print("📊 Общая статистика по резюме")
    print("-" * 40)
    print(f"Всего записей резюме: {total_records}")
    print(f"Уникальных резюме (по id): {len(unique_ids)}")
    print(f"Дубликатов: {total_records - len(unique_ids)}")

    print("\n📂 Распределение по файлам:")
    for fname, cnt in sorted(per_query_count.items()):
        print(f"{fname}: {cnt}")


if __name__ == "__main__":
    main()
