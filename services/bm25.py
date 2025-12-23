import json
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from tqdm import tqdm
import numpy as np

# --- Очистка requirements (ваш код) ---
NOISE_PATTERNS = [
    r"\bо\s+нас\b.*?(?=(требования|задачи|ждем|наш\s+кандидат|$))",
    r"\bо\s+компании\b.*?(?=(требования|задачи|ждем|наш\s+кандидат|$))",
    r"\bо\s+компании[-\s]*заказчике\b.*?(?=(требования|задачи|ждем|наш\s+кандидат|$))",
    r"\bчто\s+предлагаем\b.*",
    r"\bчто\s+мы\s+предлагаем\b.*",
    r"\bусловия\s+работы\b.*",
    r"\bпреимущества\s+работы\b.*",
    r"\bмы\s+предлагаем\b.*",
    r"\bкомпенсация\b.*",
    r"\bдмс\b.*",
    r"\bкорпоратив\b.*",
    r"\bкарьерн\w*\s+рост\b.*",
    r"\bтаймтрекер\b.*",
    r"\bотпуск\w*\b.*",
    r"\bофис\w*\b.*",
    r"\bбесплатн\w*\s+кофе\b.*",
    r"\bсобеседовани\w*\b.*",
    r"\bтестов\w*\s+задани\w*\b.*",
]

def remove_noise_requirements(text: str) -> str:
    if not text:
        return ""
    cleaned = text.lower()
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

# --- Функции ---
def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def tokenize(text):
    return text.lower().split() if text else []

def normalize(scores):
    arr = np.array(scores, float)
    if arr.size == 0:
        return []
    if arr.max() == arr.min():
        return [1.0 if s > 0 else 0.0 for s in arr]
    return ((arr - arr.min()) / (arr.max() - arr.min())).tolist()

# --- Пути ---
resumes_folder = Path("../data/prepared/resumes/cleaned/classical/")
vacancies_folder = Path("../data/prepared/vacancies/cleaned/classical/")
output_folder = Path("../data/results/bm25_results/")
output_folder.mkdir(parents=True, exist_ok=True)

weights = {
    "title": 2.0,
    "skills": 3.0,
    "experience": 1.0,
    "positions": 2.0
}

# --- Обработка ---
for vacancy_file in vacancies_folder.glob("vacancies_*.json"):
    query = vacancy_file.stem.replace("vacancies_", "")
    resume_file = resumes_folder / f"resumes_{query}.json"

    if not resume_file.exists():
        print(f"[!] Нет резюме для query {query}, пропускаем")
        continue

    resumes = load_json_file(resume_file)
    vacancies = load_json_file(vacancy_file)

    # Очистка requirements
    for v in vacancies:
        v["requirements"] = remove_noise_requirements(v.get("requirements", ""))

    # Готовим раздельные корпусы по полям
    corpuses = {field: [] for field in weights}
    for r in resumes:
        for field in weights:
            if field == "positions":
                text = " ".join(r.get("positions", []))
            else:
                text = r.get(field, r.get("experience", ""))  # поддержка старого формата
            corpuses[field].append(tokenize(text))

    # Создаём BM25 для каждого поля
    bm25_models = {}
    for field, corpus in corpuses.items():
        if any(corpus):
            bm25_models[field] = BM25Okapi(corpus)
        else:
            bm25_models[field] = None

    resume_ids = [r["id"] for r in resumes]

    # Сравнение: каждая вакансия ищет кандидатов
    results = []
    for v in tqdm(vacancies, desc=f"Ranking vacancies [{query}]"):
        field_scores = {}
        total_score = np.zeros(len(resume_ids))

        for field, weight in weights.items():
            model = bm25_models.get(field)
            if model is None or model is None:
                scores = [0.0] * len(resume_ids)
            else:
                if field == "positions":
                    query_text = v.get("title", "")
                else:
                    query_text = v.get(field, "") or v.get("requirements", "") or v.get("experience_text","")
                tokens = tokenize(query_text)
                scores = model.get_scores(tokens)

            scores = normalize(scores)
            field_scores[field] = scores
            total_score += np.array(scores) * weight

        # Итоговый скор
        max_w = sum(weights.values())
        final_scores = (total_score / max_w).clip(0, 1)

        candidates = [
            {"resume_id": resume_ids[i], "score": round(final_scores[i], 4), "field_scores": {
                f: round(field_scores[f][i], 4) for f in field_scores
            }}
            for i in range(len(resume_ids))
        ]

        candidates_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)

        results.append({
            "vacancy_id": v["id"],
            "candidates": candidates_sorted
        })

    # Сохраняем
    out_path = output_folder / f"bm25_{query}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Query {query} обработан → {out_path}")
