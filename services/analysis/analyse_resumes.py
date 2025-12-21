import json
from pathlib import Path
from collections import Counter, defaultdict

RESUMES_DIR = Path("../../data/raw/full/resumes")


def load_resumes():
    resumes = []
    for file_path in RESUMES_DIR.glob("resumes_*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                resumes.extend(data)
    return resumes


def analyze_top_level_fields(resumes):
    """
    Считает для каждого поля:
      - в скольких резюме оно присутствует
      - в скольких резюме оно заполнено
    """
    present_counter = Counter()
    filled_counter = Counter()

    for r in resumes:
        for field, value in r.items():
            present_counter[field] += 1
            if value not in (None, "", [], {}):
                filled_counter[field] += 1

    return present_counter, filled_counter


def analyze_text_fields(resumes, fields):
    stats = defaultdict(lambda: {"filled": 0, "empty": 0})

    for r in resumes:
        for field in fields:
            value = r.get(field)
            if value not in (None, "", [], {}):
                stats[field]["filled"] += 1
            else:
                stats[field]["empty"] += 1

    return stats


def main():
    resumes = load_resumes()
    total = len(resumes)

    print(f"Всего резюме: {total}\n")

    # 1. Поля верхнего уровня
    present_fields, filled_fields = analyze_top_level_fields(resumes)

    print("📌 Поля верхнего уровня (присутствует / заполнено):")
    for field, cnt in present_fields.most_common():
        filled_cnt = filled_fields.get(field, 0)
        filled_pct = filled_cnt / total * 100
        print(f"{field}: присутствует {cnt}, заполнено {filled_cnt} ({filled_pct:.1f}%)")

    # 2. Ключевые текстовые поля hh.ru
    text_fields = [
        "title",
        "skills",
        "experience",
        "education",
        "certificate",
        "summary",
        "language",
    ]

    stats = analyze_text_fields(resumes, text_fields)

    print("\n📌 Заполненность ключевых текстовых полей:")
    for field, s in stats.items():
        filled_pct = s["filled"] / total * 100
        print(f"{field}: заполнено {s['filled']} ({filled_pct:.1f}%)")


if __name__ == "__main__":
    main()
