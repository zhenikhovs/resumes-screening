"""
Pipeline ранжирования для классических данных (classical).

Входные данные: готовые обработанные файлы
  - data/prepared/resumes/cleaned/classical/resumes_<query>.json
  - data/prepared/vacancies/cleaned/classical/vacancies_<query>.json

Similarity: BM25 или TF-IDF (method="bm25" / "tfidf"). Результаты: pipeline_classical_*.json (BM25), pipeline_tfidf_*.json (TF-IDF).
"""
from pathlib import Path
from tqdm import tqdm
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer

from config.paths import (
    RESUMES_CLASSICAL,      # data/prepared/resumes/cleaned/classical
    VACANCIES_CLASSICAL,    # data/prepared/vacancies/cleaned/classical
    PIPELINE_CLASSICAL_RESULTS,
    PIPELINE_STATS_DIR,
)
from services.utils import load_json, save_json
from services.preprocessing.clean_text import remove_noise_requirements
from services.ranking.score_utils import tokenize, normalize_scores
from services.ranking.pipeline_common import (
    run_pipeline_for_vacancy,
    compute_global_statistics,
)


def resume_to_text(r: dict) -> str:
    """Один текст резюме для similarity (classical)."""
    title = r.get("title", "") or ""
    positions = r.get("positions") or []
    pos_str = " ".join(positions) if isinstance(positions, list) else str(positions)
    skills = r.get("skills", "") or ""
    experience = r.get("experience", "") or ""
    return " ".join([title, pos_str, skills, experience])


def vacancy_to_text(v: dict) -> str:
    """Один текст вакансии для similarity (classical)."""
    title = v.get("title", "") or ""
    skills = v.get("skills", "") or ""
    req = v.get("requirements", "") or ""
    return " ".join([title, skills, req])


def make_bm25_similarity_getter(_resumes_full: list):
    """
    Возвращает функцию get_similarity_scores(vacancy, filtered_resumes) -> list[float].
    Для каждого вакансии строит BM25 по корпусу filtered_resumes, возвращает нормализованные [0,1] скоры.
    """
    def get_similarity_scores(vacancy: dict, filtered_resumes: list, filtered_indices=None) -> list:
        if not filtered_resumes:
            return []
        corpus = [tokenize(resume_to_text(r)) for r in filtered_resumes]
        if not any(corpus):
            return [0.0] * len(filtered_resumes)
        bm25 = BM25Okapi(corpus)
        query_tok = tokenize(vacancy_to_text(vacancy))
        raw = bm25.get_scores(query_tok)
        return normalize_scores(raw.tolist())
    return get_similarity_scores


def make_tfidf_similarity_getter(_resumes_full: list):
    """
    Возвращает функцию get_similarity_scores(vacancy, filtered_resumes) -> list[float].
    Для каждой вакансии строит TF-IDF по корпусу filtered_resumes (тексты как строки), возвращает нормализованные [0,1] скоры.
    """
    def get_similarity_scores(vacancy: dict, filtered_resumes: list, filtered_indices=None) -> list:
        if not filtered_resumes:
            return []
        corpus = [resume_to_text(r) for r in filtered_resumes]
        if not any(c.strip() for c in corpus):
            return [0.0] * len(filtered_resumes)
        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(corpus)
        q = vectorizer.transform([vacancy_to_text(vacancy)])
        raw = (X @ q.T).toarray().flatten()
        return normalize_scores(raw.tolist())
    return get_similarity_scores


def run_pipeline_classical(method: str = "bm25"):
    """
    Запускает новый pipeline для classical данных.
    method: "bm25" (по умолчанию) или "tfidf" — способ вычисления similarity.
    """
    PIPELINE_CLASSICAL_RESULTS.mkdir(parents=True, exist_ok=True)
    PIPELINE_STATS_DIR.mkdir(parents=True, exist_ok=True)

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
        if method == "tfidf":
            get_similarity = make_tfidf_similarity_getter(resumes)
            out_prefix = "pipeline_tfidf"
        else:
            get_similarity = make_bm25_similarity_getter(resumes)
            out_prefix = "pipeline_classical"  # BM25

        all_results = []
        for v in tqdm(vacancies, desc=f"Pipeline {method} [{query}]"):
            result = run_pipeline_for_vacancy(
                vacancy=v,
                resumes=resumes,
                resume_ids=resume_ids,
                get_similarity_scores=get_similarity,
            )
            all_results.append(result)

        out_path = PIPELINE_CLASSICAL_RESULTS / f"{out_prefix}_{query}.json"
        save_json(out_path, all_results)
        print(f"[+] Pipeline {method} {query} → {out_path}")

        stats = compute_global_statistics(all_results)
        stats_path = PIPELINE_STATS_DIR / f"{out_prefix}_{query}_stats.json"
        save_json(stats_path, stats)
        print(f"[+] Статистика → {stats_path}")

    print(f"[+] Pipeline {method} завершён.")


if __name__ == "__main__":
    run_pipeline_classical()
