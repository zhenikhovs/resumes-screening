"""
Ранжирование кандидатов по вакансии с помощью BM25 по полям.

- BM25Okapi (библиотека rank_bm25): классическая формула BM25 из Okapi IR system;
  учитывает частоту терминов, IDF и длину документа. Нужна для воспроизводимого
  и стандартного BM25-ранжирования.
- Итоговый score: взвешенная сумма по полям (title, skills, experience, experience_months),
  затем min-max по кандидатам каждой вакансии → [0, 1]. Так методы сопоставимы.
- «Ранжирует лучше» = у метода выше NDCG/MAP/MRR на одной и той же разметке:
  релевантные кандидаты (топ-k по эталону) оказываются выше в списке.
  См. docs/RANKING_METRICS_AND_BETTER.md.
"""
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from tqdm import tqdm

from config.paths import RESUMES_CLASSICAL, VACANCIES_CLASSICAL, BM25_RESULTS
from config.ranking_weights import CLASSICAL_WEIGHTS
from services.utils import load_json, save_json
from services.preprocessing.clean_text import remove_noise_requirements
from services.ranking.score_utils import tokenize, normalize_scores

BM25_RESULTS.mkdir(parents=True, exist_ok=True)

WEIGHTS = CLASSICAL_WEIGHTS
# Параметры BM25 (k1 — насыщение частоты термина, b — штраф за длину документа).
# Дефолты rank_bm25: k1=1.5, b=0.75. Для настройки под корпус можно передать в BM25Okapi(..., k1=1.2, b=0.6).


def run_bm25():
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
        title_corpus = [tokenize(r.get("title", "") + " " + " ".join(r.get("positions", []))) for r in resumes]
        skills_corpus = [tokenize(r.get("skills", "")) for r in resumes]
        experience_corpus = [tokenize(r.get("experience", "")) for r in resumes]

        bm25_title = BM25Okapi(title_corpus) if any(title_corpus) else None
        bm25_skills = BM25Okapi(skills_corpus) if any(skills_corpus) else None
        bm25_experience = BM25Okapi(experience_corpus) if any(experience_corpus) else None

        results = []
        n_resumes = len(resumes)
        max_weight = sum(WEIGHTS.values())

        for v in tqdm(vacancies, desc=f"BM25 [{query}]"):
            total_score = np.zeros(n_resumes)

            if bm25_title:
                title_scores = normalize_scores(bm25_title.get_scores(tokenize(v.get("title", ""))))
            else:
                title_scores = [0.0] * n_resumes
            total_score += np.array(title_scores) * WEIGHTS["title"]

            if bm25_skills:
                skills_scores = normalize_scores(bm25_skills.get_scores(tokenize(v.get("skills", ""))))
            else:
                skills_scores = [0.0] * n_resumes
            total_score += np.array(skills_scores) * WEIGHTS["skills"]

            if bm25_experience:
                exp_scores = normalize_scores(bm25_experience.get_scores(tokenize(v.get("requirements", ""))))
            else:
                exp_scores = [0.0] * n_resumes
            total_score += np.array(exp_scores) * WEIGHTS["experience"]

            min_exp_v = v.get("min_experience_months")
            max_exp_v = v.get("max_experience_months")
            exp_scores_months = []
            for r in resumes:
                try:
                    total_exp = int(r.get("total_experience_months", 0))
                except (TypeError, ValueError):
                    total_exp = 0
                score = 0.0
                if min_exp_v is not None:
                    min_i = int(min_exp_v)
                    if total_exp >= min_i and (max_exp_v is None or total_exp <= int(max_exp_v)):
                        score = 1.0
                exp_scores_months.append(score)
            total_score += np.array(exp_scores_months) * WEIGHTS["experience_months"]

            # Каждое поле уже нормализовано в [0,1], сумма/max_weight ∈ [0,1]. clip избыточен.
            raw_final = total_score / max_weight
            final_scores = normalize_scores(raw_final.tolist())

            candidates = [
                {
                    "resume_id": resume_ids[i],
                    "score": round(final_scores[i], 4),
                    "field_scores": {
                        "title": round(title_scores[i], 4),
                        "skills": round(skills_scores[i], 4),
                        "experience": round(exp_scores[i], 4),
                        "experience_months": round(exp_scores_months[i], 4),
                    },
                }
                for i in range(n_resumes)
            ]
            candidates_sorted = sorted(candidates, key=lambda x: x["score"], reverse=True)
            results.append({"vacancy_id": v["id"], "candidates": candidates_sorted})

        out_path = BM25_RESULTS / f"bm25_{query}.json"
        save_json(out_path, results)
        print(f"[+] BM25 {query} → {out_path}")


if __name__ == "__main__":
    run_bm25()
