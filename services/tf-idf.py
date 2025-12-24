import json
import re
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
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

def remove_noise(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# --- Пути ---
resumes_folder = Path("../data/prepared/resumes/cleaned/classical/")
vacancies_folder = Path("../data/prepared/vacancies/cleaned/classical/")
output_folder = Path("../data/results/tfidf_results/")
output_folder.mkdir(parents=True, exist_ok=True)

# --- Веса полей ---
weights = {
    "title": 2.0,
    "skills": 3.0,
    "experience_text": 1.0,
    "experience_months": 1.0
}

# --- Функции для текста ---
def prepare_resume_text(r, field):
    if field == "title":
        return r.get("title", "") + " " + " ".join(r.get("positions", []))
    elif field == "skills":
        return r.get("skills", "")
    elif field == "experience_text":
        return r.get("experience", "") or r.get("requirements", "")
    return ""

def prepare_vacancy_text(v, field):
    if field == "title":
        return v.get("title", "")
    elif field == "skills":
        return v.get("skills", "")
    elif field == "experience_text":
        return v.get("requirements", "") or v.get("experience_text", "")
    return ""

# --- Обработка вакансий ---
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
        v["requirements"] = remove_noise(v.get("requirements", ""))

    resume_ids = [r["id"] for r in resumes]
    n_resumes = len(resumes)

    # --- Корпуса TF-IDF для каждого поля ---
    tfidf_models = {}
    tfidf_matrices = {}
    text_fields = ["title", "skills", "experience_text"]

    for field in text_fields:
        corpus = [prepare_resume_text(r, field) for r in resumes]
        if any(corpus):
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform(corpus)
            tfidf_models[field] = vectorizer
            tfidf_matrices[field] = tfidf_matrix
        else:
            tfidf_models[field] = None
            tfidf_matrices[field] = None

    results = []

    for v in tqdm(vacancies, desc=f"Ranking vacancies [{query}]"):
        total_score = np.zeros(n_resumes)
        field_scores = {}

        # --- Считаем TF-IDF по каждому полю ---
        for field in text_fields:
            if tfidf_models[field] is not None:
                query_vec = tfidf_models[field].transform([prepare_vacancy_text(v, field)])
                scores = (tfidf_matrices[field] @ query_vec.T).toarray().flatten()
                scores = normalize(scores.reshape(1, -1)).flatten()
            else:
                scores = np.zeros(n_resumes)
            total_score += scores * weights[field]
            field_scores[field] = scores

        # --- Опыт в месяцах ---
        exp_scores = []
        min_exp = v.get("min_experience_months")
        max_exp = v.get("max_experience_months")
        for r in resumes:
            try:
                total_exp = int(r.get("total_experience_months", 0))
            except:
                total_exp = 0
            score = 0.0
            if min_exp is not None and total_exp >= int(min_exp):
                if max_exp is None or total_exp <= int(max_exp):
                    score = 1.0
            exp_scores.append(score)
        total_score += np.array(exp_scores) * weights["experience_months"]
        field_scores["experience_months"] = exp_scores

        # --- Финальная нормализация ---
        final_scores = (total_score / sum(weights.values())).clip(0, 1)

        candidates = [
            {
                "resume_id": resume_ids[i],
                "score": round(final_scores[i], 4),
                "field_scores": {f: round(field_scores[f][i], 4) for f in field_scores}
            } for i in range(n_resumes)
        ]
        candidates_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)
        results.append({
            "vacancy_id": v["id"],
            "candidates": candidates_sorted
        })

    # --- Сохраняем ---
    out_path = output_folder / f"tfidf_{query}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[+] Query {query} обработан → {out_path}")
