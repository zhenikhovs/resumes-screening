"""
Общая логика нового pipeline ранжирования.

Шаги: фильтр по опыту → similarity → final_score → min-max → сортировка → 90% порог → top-K.
Кандидаты, не прошедшие фильтр по опыту, исключаются из ранжирования (не участвуют в similarity).
"""
from __future__ import annotations
import numpy as np
from typing import Callable
from config.pipeline_config import (
    EXPERIENCE_FACTOR,
    SIMILARITY_WEIGHT,
    EXPERIENCE_MATCH_WEIGHT,
    PERCENTILE_THRESHOLD,
    TOP_K,
)


def vacancy_required_experience_months(vacancy: dict) -> int:
    """Требуемый опыт вакансии в месяцах (min_experience_months или 0)."""
    v = vacancy.get("min_experience_months")
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def resume_experience_months(resume: dict) -> int:
    """Опыт кандидата в месяцах."""
    v = resume.get("total_experience_months")
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def experience_match_value(resume: dict, vacancy: dict) -> int:
    """
    1 — стаж не ниже vacancy.min_experience_months (полный минимум вакансии).
    0 — в пуле по мягкому фильтру 0.8×min, но стаж ниже полного минимума.
    Если min не задан (0), у прошедших в пул считается 1.
    """
    req = vacancy_required_experience_months(vacancy)
    if req <= 0:
        return 1
    return 1 if resume_experience_months(resume) >= req else 0


def experience_filter(resumes: list, vacancy: dict) -> tuple[list, list, list]:
    """
    Жёсткий отбор в пул: experience >= 0.8 * vacancy_min.
    Третий список — passed_filter[i] (1/0), не experience_match.
    """
    req = vacancy_required_experience_months(vacancy)
    threshold = max(0, int(EXPERIENCE_FACTOR * req))
    filtered = []
    indices = []
    passed_filter = []
    for i, r in enumerate(resumes):
        exp = resume_experience_months(r)
        passes = exp >= threshold
        passed_filter.append(1 if passes else 0)
        if passes:
            filtered.append(r)
            indices.append(i)
    return filtered, indices, passed_filter


def min_max_normalize(scores: list) -> list:
    """Min-max по списку: (x - min) / (max - min), в [0, 1]."""
    arr = np.asarray(scores, dtype=float)
    if arr.size == 0:
        return []
    if np.all(arr == arr.flat[0]):
        return [1.0 if s > 0 else 0.0 for s in arr]
    min_val, max_val = arr.min(), arr.max()
    if max_val == min_val:
        return [1.0 if s > 0 else 0.0 for s in arr]
    return ((arr - min_val) / (max_val - min_val)).tolist()


def run_pipeline_for_vacancy(
    vacancy: dict,
    resumes: list,
    resume_ids: list,
    get_similarity_scores: Callable[..., list],
) -> dict:
    """
    Выполняет pipeline для одной вакансии.

    get_similarity_scores(vacancy, filtered_resumes, filtered_indices=None) -> list[float].
    Третий аргумент filtered_indices опционален (для transformer с предвычисленными эмбеддингами).
    """
    n_before_filter = len(resumes)
    filtered_resumes, filtered_indices, _passed_filter = experience_filter(resumes, vacancy)
    n_after_filter = len(filtered_resumes)

    if n_after_filter == 0:
        return {
            "vacancy_id": vacancy.get("id"),
            "n_resumes_before_filter": n_before_filter,
            "n_resumes_after_filter": 0,
            "candidates": [],
            "threshold": None,
            "top_k_candidates": [],
            "similarity_scores": [],
            "final_scores": [],
            "score_norm": [],
        }

    similarity_scores = get_similarity_scores(vacancy, filtered_resumes, filtered_indices)
    experience_match_filtered = [
        experience_match_value(r, vacancy) for r in filtered_resumes
    ]
    final_scores = [
        SIMILARITY_WEIGHT * sim + EXPERIENCE_MATCH_WEIGHT * em
        for sim, em in zip(similarity_scores, experience_match_filtered)
    ]
    score_norm = min_max_normalize(final_scores)

    # Сортируем по score_norm по убыванию
    order = np.argsort(score_norm)[::-1].tolist()
    sorted_ids = [filtered_resumes[j]["id"] for j in order]
    sorted_similarity = [similarity_scores[j] for j in order]
    sorted_final = [final_scores[j] for j in order]
    sorted_norm = [score_norm[j] for j in order]

    threshold = float(np.percentile(score_norm, PERCENTILE_THRESHOLD))
    above = [i for i, s in enumerate(sorted_norm) if s >= threshold]
    top_indices = above[:TOP_K]
    top_k_candidates = [
        {
            "resume_id": sorted_ids[i],
            "similarity_score": round(sorted_similarity[i], 4),
            "experience_match": experience_match_filtered[order[i]],
            "final_score": round(sorted_final[i], 4),
            "score_norm": round(sorted_norm[i], 4),
        }
        for i in top_indices
    ]

    candidates_full = [
        {
            "resume_id": filtered_resumes[j]["id"],
            "similarity_score": round(similarity_scores[j], 4),
            "experience_match": experience_match_filtered[j],
            "final_score": round(final_scores[j], 4),
            "score_norm": round(score_norm[j], 4),
        }
        for j in range(len(filtered_resumes))
    ]
    candidates_sorted = sorted(candidates_full, key=lambda x: x["score_norm"], reverse=True)

    return {
        "vacancy_id": vacancy.get("id"),
        "n_resumes_before_filter": n_before_filter,
        "n_resumes_after_filter": n_after_filter,
        "similarity_scores": [round(s, 4) for s in similarity_scores],
        "final_scores": [round(s, 4) for s in final_scores],
        "score_norm": [round(s, 4) for s in score_norm],
        "threshold": round(threshold, 4),
        "candidates": candidates_sorted,
        "top_k_candidates": top_k_candidates,
    }


def compute_global_statistics(all_vacancy_results: list) -> dict:
    """Собирает статистику по всем вакансиям."""
    n_after_filter = [r["n_resumes_after_filter"] for r in all_vacancy_results if r["n_resumes_after_filter"] is not None]
    n_after_threshold = []
    n_final = []
    all_similarity = []
    all_score_norm = []
    thresholds = []

    for r in all_vacancy_results:
        if r["n_resumes_after_filter"] == 0:
            continue
        n_final.append(len(r["top_k_candidates"]))
        candidates = r.get("candidates", [])
        above_th = sum(1 for c in candidates if c["score_norm"] >= r["threshold"])
        n_after_threshold.append(above_th)
        all_similarity.extend(r.get("similarity_scores", []))
        all_score_norm.extend(r.get("score_norm", []))
        if r.get("threshold") is not None:
            thresholds.append(r["threshold"])

    def safe_mean(arr):
        return float(np.mean(arr)) if arr else 0.0

    def safe_min_max(arr):
        if not arr:
            return None, None
        return float(min(arr)), float(max(arr))

    return {
        "mean_candidates_after_experience_filter": safe_mean(n_after_filter),
        "mean_candidates_after_threshold": safe_mean(n_after_threshold) if n_after_threshold else 0.0,
        "mean_final_candidates": safe_mean(n_final) if n_final else 0.0,
        "min_max_candidates_after_filter": safe_min_max(n_after_filter),
        "min_max_final_candidates": safe_min_max(n_final) if n_final else (None, None),
        "similarity_distribution": {
            "min": float(np.min(all_similarity)) if all_similarity else None,
            "max": float(np.max(all_similarity)) if all_similarity else None,
            "mean": float(np.mean(all_similarity)) if all_similarity else None,
        },
        "score_norm_distribution": {
            "min": float(np.min(all_score_norm)) if all_score_norm else None,
            "max": float(np.max(all_score_norm)) if all_score_norm else None,
            "mean": float(np.mean(all_score_norm)) if all_score_norm else None,
        },
        "threshold_per_vacancy": thresholds,
        "threshold_mean": float(np.mean(thresholds)) if thresholds else None,
    }
