import json
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from tqdm import tqdm
import numpy as np

# --- Очистка requirements ---
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

# --- Базовые функции ---
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

# --- Папки ---
resumes_folder = Path("../data/prepared/resumes/cleaned/classical/")
vacancies_folder = Path("../data/prepared/vacancies/cleaned/classical/")
output_folder = Path("../data/results/bm25_results/")
output_folder.mkdir(parents=True, exist_ok=True)

# Веса полей
weights = {
    "title": 2.0,
    "skills": 3.0,
    "experience": 1.0,
    "experience_months": 1.0
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

    resume_ids = [r["id"] for r in resumes]

    # --- Корпуса для BM25 ---
    title_corpus = [tokenize(r.get("title", "") + " " + " ".join(r.get("positions", []))) for r in resumes]
    skills_corpus = [tokenize(r.get("skills", "")) for r in resumes]
    experience_corpus = [tokenize(r.get("experience", "")) for r in resumes]

    bm25_title = BM25Okapi(title_corpus) if any(title_corpus) else None
    bm25_skills = BM25Okapi(skills_corpus) if any(skills_corpus) else None
    bm25_experience = BM25Okapi(experience_corpus) if any(experience_corpus) else None

    results = []

    for v in tqdm(vacancies, desc=f"Ranking vacancies [{query}]"):
        n_resumes = len(resumes)
        total_score = np.zeros(n_resumes)

        # --- Title ↔ title+positions ---
        if bm25_title:
            title_tokens = tokenize(v.get("title", ""))
            title_scores = bm25_title.get_scores(title_tokens)
            title_scores = normalize(title_scores)
        else:
            title_scores = [0.0] * n_resumes
        total_score += np.array(title_scores) * weights["title"]

        # --- Skills ↔ skills ---
        skills_scores = []
        vac_skills_set = set(tokenize(v.get("skills", "")))
        for r in resumes:
            resume_skills_set = set(tokenize(r.get("skills", "")))
            if vac_skills_set:
                matched_ratio = len(vac_skills_set & resume_skills_set) / len(vac_skills_set)
                skills_scores.append(matched_ratio)
            else:
                skills_scores.append(0.0)
        total_score += np.array(skills_scores) * weights["skills"]

        # --- Requirements ↔ experience ---
        if bm25_experience:
            req_tokens = tokenize(v.get("requirements", ""))
            exp_scores = bm25_experience.get_scores(req_tokens)
            exp_scores = normalize(exp_scores)
        else:
            exp_scores = [0.0] * n_resumes
        total_score += np.array(exp_scores) * weights["experience"]

        # --- Опыт (total_experience_months) ---
        exp_scores_months = []
        min_exp = v.get("min_experience_months")
        max_exp = v.get("max_experience_months")
        for r in resumes:
            try:
                total_exp = int(r.get("total_experience_months", 0))
            except:
                total_exp = 0
            score = 0.0
            if min_exp is not None:
                min_exp = int(min_exp)
                if total_exp >= min_exp and (max_exp is None or total_exp <= int(max_exp)):
                    score = 1.0
            exp_scores_months.append(score)
        total_score += np.array(exp_scores_months) * weights["experience_months"]

        # --- Финальная нормализация ---
        max_weight = sum(weights.values())
        final_scores = (total_score / max_weight).clip(0,1)

        candidates = [
            {
                "resume_id": resume_ids[i],
                "score": round(final_scores[i],4),
                "field_scores": {
                    "title": round(title_scores[i],4),
                    "skills": round(skills_scores[i],4),
                    "experience": round(exp_scores[i],4),
                    "experience_months": round(exp_scores_months[i],4)
                }
            } for i in range(n_resumes)
        ]

        candidates_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)
        results.append({
            "vacancy_id": v["id"],
            "candidates": candidates_sorted
        })

    # --- Сохранение ---
    out_path = output_folder / f"bm25_{query}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[+] Query {query} обработан → {out_path}")
