from pathlib import Path

# Список директорий
paths = [
    "../data/raw/full/resumes",
    "../data/raw/full/vacancies",
    "../data/prepared/resumes/pre-cleaned",
    "../data/prepared/vacancies/pre-cleaned",
    "../data/prepared/resumes/cleaned/classical",
    "../data/prepared/resumes/cleaned/transformer",
    "../data/prepared/vacancies/cleaned/classical",
    "../data/prepared/vacancies/cleaned/transformer",
]

for dir_path in paths:
    p = Path(dir_path)
    if not p.exists():
        print(f"❌ Директория не найдена: {dir_path}")
        continue

    total_lines = 0
    print(f"\n📂 {dir_path}")
    for file in sorted(p.glob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                lines = sum(1 for _ in f)
                total_lines += lines
                print(f"  {file.name}: {lines} строк")
        except Exception as e:
            print(f"⚠ Ошибка чтения {file.name}: {e}")

    print(f"  ➤ Всего строк в папке: {total_lines}")
