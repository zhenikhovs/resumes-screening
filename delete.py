import json
import os

raw_path = "data/raw/resumes_raw.json"

if not os.path.exists(raw_path):
    print(f"❌ Файл {raw_path} не найден")
    exit(1)

with open(raw_path, "r", encoding="utf-8") as f:
    resumes = json.load(f)

# ID резюме для удаления
remove_id = "cb9bd796000857eade0017a1e64e6650434c45"

# Фильтруем список
resumes = [r for r in resumes if r.get("id") != remove_id]

with open(raw_path, "w", encoding="utf-8") as f:
    json.dump(resumes, f, ensure_ascii=False, indent=2)

print(f"✅ Резюме {remove_id} удалено. Всего осталось {len(resumes)} резюме.")
