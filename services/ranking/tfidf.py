"""
Ранжирование кандидатов по вакансии с помощью TF-IDF по полям.
Итоговый score нормализуется min-max по кандидатам каждой вакансии → [0, 1].
Сопоставимо с BM25 и другими методами по шкале и по метрикам (NDCG, MAP).
"""
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize as sklearn_normalize
from tqdm import tqdm

from config.paths import RESUMES_CLASSICAL, VACANCIES_CLASSICAL, TFIDF_RESULTS
from config.ranking_weights import TFIDF_WEIGHTS
from services.utils import load_json, save_json
from services.preprocessing.clean_text import remove_noise_requirements
from services.ranking.score_utils import normalize_scores

TFIDF_RESULTS.mkdir(parents=True, exist_ok=True)
WEIGHTS = TFIDF_WEIGHTS
TEXT_FIELDS = ["title", "skills", "experience_text"]


def _prepare_resume_text(r, field):
    if field == "title":
        return r.get("title", "") + " " + " ".join(r.get("positions", []))
    if field == "skills":
        return r.get("skills", "")
    if field == "experience_text":
        return r.get("experience", "") or r.get("requirements", "")
    return ""


def _prepare_vacancy_text(v, field):
    if field == "title":
        return v.get("title", "")
    if field == "skills":
        return v.get("skills", "")
    if field == "experience_text":
        return v.get("requirements", "") or v.get("experience_text", "")
    return ""


def run_tfidf():
    for vacancy_file in sorted(VACANCIES_CLASSICAL.glob("vacancies_*.json")):
        query = vacancy_file.stem.replace("vacancies_", "")
        resume_file = RESUMES_CLASSICAL / f"resumes_{query}.json"
        if not resume_file.exists():
            print(f"[!] Нет резюме для query {query}, пропускаем")
            continue

        resumes = load_json(resume_file)
        vacancies = load_json(vacancy_file)
        for v in vacancies:
            v["requirements"] = remove_noise_requirements(v.get("requirements", ""))

        resume_ids = [r["id"] for r in resumes]
        n_resumes = len(resumes)
        tfidf_models = {}
        tfidf_matrices = {}

        for field in TEXT_FIELDS:
            corpus = [_prepare_resume_text(r, field) for r in resumes]
            if any(corpus):
                vectorizer = TfidfVectorizer()
                tfidf_matrices[field] = vectorizer.fit_transform(corpus)
                tfidf_models[field] = vectorizer
            else:
                tfidf_models[field] = None
                tfidf_matrices[field] = None

        results = []
        for v in tqdm(vacancies, desc=f"TF-IDF [{query}]"):
            total_score = np.zeros(n_resumes)
            field_scores = {}

            for field in TEXT_FIELDS:
                if tfidf_models[field] is not None:
                    query_vec = tfidf_models[field].transform([_prepare_vacancy_text(v, field)])
                    scores = (tfidf_matrices[field] @ query_vec.T).toarray().flatten()
                    scores = sklearn_normalize(scores.reshape(1, -1)).flatten()
                else:
                    scores = np.zeros(n_resumes)
                total_score += scores * WEIGHTS[field]
                field_scores[field] = scores

            min_exp = v.get("min_experience_months")
            max_exp = v.get("max_experience_months")
            exp_scores = []
            for r in resumes:
                try:
                    total_exp = int(r.get("total_experience_months", 0))
                except (TypeError, ValueError):
                    total_exp = 0
                score = 0.0
                if min_exp is not None and total_exp >= int(min_exp):
                    if max_exp is None or total_exp <= int(max_exp):
                        score = 1.0
                exp_scores.append(score)
            total_score += np.array(exp_scores) * WEIGHTS["experience_months"]
            field_scores["experience_months"] = np.array(exp_scores)

            # Скоры TF-IDF (cosine) могут быть < 0, поэтому clip(0, 1) нужен.
            raw_final = (total_score / sum(WEIGHTS.values())).clip(0, 1)
            final_scores = normalize_scores(raw_final.tolist())

            candidates = [
                {
                    "resume_id": resume_ids[i],
                    "score": round(final_scores[i], 4),
                    "field_scores": {f: round(float(field_scores[f][i]), 4) for f in field_scores},
                }
                for i in range(n_resumes)
            ]
            candidates_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)
            results.append({"vacancy_id": v["id"], "candidates": candidates_sorted})

        out_path = TFIDF_RESULTS / f"tfidf_{query}.json"
        save_json(out_path, results)
        print(f"[+] TF-IDF {query} → {out_path}")


if __name__ == "__main__":
    run_tfidf()
