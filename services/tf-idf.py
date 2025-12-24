import json
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from tqdm import tqdm
import numpy as np

# --- Функции ---
def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def combine_resume_text(r, weights):
    texts = []
    for field, w in weights.items():
        if field == "positions":
            text = " ".join(r.get("positions", []))
        else:
            text = r.get(field, "")
        texts.append(text)
    return " ".join(texts)

def combine_vacancy_text(v, field):
    if field == "positions":
        return v.get("title", "")
    else:
        return v.get(field, "") or v.get("requirements", "") or v.get("experience_text", "")

# --- Пути ---
resumes_folder = Path("../data/prepared/resumes/cleaned/classical/")
vacancies_folder = Path("../data/prepared/vacancies/cleaned/classical/")
output_folder = Path("../data/results/tfidf_results/")
output_folder.mkdir(parents=True, exist_ok=True)

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

    resume_texts = [combine_resume_text(r, weights) for r in resumes]
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(resume_texts)

    resume_ids = [r["id"] for r in resumes]

    results = []
    for v in tqdm(vacancies, desc=f"Ranking vacancies [{query}]"):
        total_score = np.zeros(len(resume_ids))
        field_scores = {}

        for field, weight in weights.items():
            query_text = combine_vacancy_text(v, field)
            query_vec = vectorizer.transform([query_text])
            scores = (tfidf_matrix @ query_vec.T).toarray().flatten()
            scores = normalize(scores.reshape(1, -1)).flatten()  # нормализация 0-1
            total_score += scores * weight
            field_scores[field] = scores

        final_scores = (total_score / sum(weights.values())).clip(0, 1)
        candidates = [
            {"resume_id": resume_ids[i], "score": round(final_scores[i], 4),
             "field_scores": {f: round(field_scores[f][i], 4) for f in field_scores}}
            for i in range(len(resume_ids))
        ]
        candidates_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)
        results.append({"vacancy_id": v["id"], "candidates": candidates_sorted})

    # Сохраняем
    out_path = output_folder / f"tfidf_{query}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[+] Query {query} обработан → {out_path}")
