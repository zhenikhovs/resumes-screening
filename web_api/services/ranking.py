"""Топ кандидатов: из кэша pipeline или live-ранжирование одной вакансии."""
import json
from typing import Any

from config.paths import (
    PIPELINE_CROSS_ENCODER_RESULTS,
    PIPELINE_TRANSFORMER_RESULTS,
    RESUMES_TRANSFORMER,
    VACANCIES_TRANSFORMER,
)
from services.preprocessing.clean_vacancies import build_vacancy_transformer
from services.preprocessing.pre_clean_vacancies import clean_vacancy as pre_clean_vacancy
from services.preprocessing.resume_display import display_for_resume_id, resume_display_map
from services.ranking.cross_encoder_rerank import (
    CROSS_ENCODER_MODELS,
    _build_pairs_for_vacancy,
)
from services.ranking.pipeline_common import run_pipeline_for_vacancy
from services.ranking.pipeline_transformer import (
    TRANSFORMER_MODELS,
    _resume_text_for_embedding,
    _vacancy_text_for_embedding,
    make_similarity_getter,
)
from services.utils import load_json
from sentence_transformers import CrossEncoder, SentenceTransformer
from web_api.config import RANKING_CE_MODEL, RANKING_METHOD, RANKING_TOP_N, USE_CACHED_RANKING


def _stage_row(
    query: str,
    rank: int,
    c: dict,
    display: dict[str, dict[str, str]],
) -> dict[str, Any]:
    rid = str(c.get("resume_id", ""))
    disp = display.get(rid) or display_for_resume_id(query, rid)
    row: dict[str, Any] = {
        "rank": rank,
        "resume_id": rid,
        "position": disp.get("position") or rid,
        "summary": disp.get("summary") or "",
    }
    if c.get("similarity_score") is not None:
        row["similarity_score"] = round(float(c["similarity_score"]), 4)
    if c.get("experience_match") is not None:
        row["experience_match"] = int(c["experience_match"])
    if c.get("final_score") is not None:
        row["final_score"] = round(float(c["final_score"]), 4)
    if c.get("score_norm") is not None:
        row["score_norm"] = round(float(c["score_norm"]), 4)
    if c.get("rerank_score") is not None:
        row["rerank_score"] = round(float(c["rerank_score"]), 4)
    return row


def _candidate_row(
    query: str,
    rid: str,
    rank: int,
    score: float,
    payload: dict,
    display: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    dmap = display if display is not None else resume_display_map(query)
    disp = dmap.get(rid) or display_for_resume_id(query, rid)
    position = disp.get("position") or rid
    summary = disp.get("summary") or ""
    return {
        "resume_id": rid,
        "rank": rank,
        "score": round(score, 4),
        "position": position,
        "summary": summary,
        "title": position,
        "payload": payload,
    }


def _build_stage_lists(
    query: str,
    top_stage1: list[dict],
    ranked_after_ce: list[dict],
) -> tuple[list[dict], list[dict]]:
    display = resume_display_map(query)
    e5_sorted = sorted(top_stage1, key=lambda x: x.get("score_norm", 0), reverse=True)
    e5_rows = [
        _stage_row(query, i, c, display) for i, c in enumerate(e5_sorted, start=1)
    ]
    rerank_sorted = sorted(
        ranked_after_ce,
        key=lambda x: x.get("rerank_score", x.get("score_norm", 0)),
        reverse=True,
    )
    rerank_rows = [
        _stage_row(query, i, c, display) for i, c in enumerate(rerank_sorted, start=1)
    ]
    return e5_rows, rerank_rows


def _load_cached_rerank(query: str, vacancy_id: str) -> list[dict] | None:
    ce_path = (
        PIPELINE_CROSS_ENCODER_RESULTS
        / RANKING_METHOD
        / f"cross_encoder_{RANKING_METHOD}_{RANKING_CE_MODEL}_{query}.json"
    )
    if not ce_path.exists():
        return None
    data = load_json(ce_path) or []
    for entry in data:
        if str(entry.get("vacancy_id")) == str(vacancy_id):
            cands = entry.get("cross_encoder_candidates") or []
            if cands:
                return cands
            return entry.get("top_k_candidates") or entry.get("candidates") or []
    return None


def _load_cached_pipeline(query: str, vacancy_id: str) -> list[dict] | None:
    p_path = (
        PIPELINE_TRANSFORMER_RESULTS
        / RANKING_METHOD
        / f"pipeline_{RANKING_METHOD}_{query}.json"
    )
    if not p_path.exists():
        return None
    for entry in load_json(p_path) or []:
        if str(entry.get("vacancy_id")) == str(vacancy_id):
            return entry.get("top_k_candidates") or []
    return None


def get_top_candidates(
    query: str,
    vacancy_id: str,
    hh_vacancy_raw: dict | None = None,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    top_n = top_n or RANKING_TOP_N

    if USE_CACHED_RANKING:
        cached = _load_cached_rerank(query, vacancy_id)
        if cached is None:
            cached = _load_cached_pipeline(query, vacancy_id)
        if cached is None and vacancy_id:
            cached = _load_cached_rerank(query, vacancy_id)
            if not cached:
                all_entries = load_json(
                    PIPELINE_CROSS_ENCODER_RESULTS
                    / RANKING_METHOD
                    / f"cross_encoder_{RANKING_METHOD}_{RANKING_CE_MODEL}_{query}.json"
                ) or []
                if all_entries:
                    entry = all_entries[0]
                    cached = entry.get("cross_encoder_candidates") or entry.get("top_k_candidates") or []

        if cached:
            display = resume_display_map(query)
            return [
                _candidate_row(
                    query,
                    str(c.get("resume_id", "")),
                    i,
                    float(c.get("rerank_score", c.get("score_norm", 0))),
                    c,
                    display,
                )
                for i, c in enumerate(cached[:top_n], start=1)
            ]

    if not hh_vacancy_raw:
        raise ValueError("Нет кэша ранжирования и не передана вакансия для live-ранжирования")

    pre = pre_clean_vacancy(hh_vacancy_raw)
    pre["query"] = query
    vacancy = build_vacancy_transformer(pre)
    return _run_live_ranking_with_vacancy(query, vacancy, top_n)


def run_live_ranking_for_slug(slug: str, vacancy_id: str, top_n: int | None = None) -> dict[str, Any]:
    """Ранжирование по подготовленным camp_* файлам; возвращает final + этапы E5 и rerank."""
    top_n = top_n or RANKING_TOP_N
    vacancies = load_json(VACANCIES_TRANSFORMER / f"vacancies_{slug}.json") or []
    vacancy = next((v for v in vacancies if str(v.get("id")) == str(vacancy_id)), None)
    if not vacancy and vacancies:
        vacancy = vacancies[0]
    if not vacancy:
        raise FileNotFoundError(f"Нет cleaned-вакансии для slug={slug}")
    return _run_live_ranking_with_vacancy(slug, vacancy, top_n)


def _run_live_ranking_with_vacancy(query: str, vacancy: dict, top_n: int) -> list[dict]:
    """Transformer pipeline для одной вакансии + CE rerank по top после порога."""
    resume_path = RESUMES_TRANSFORMER / f"resumes_{query}.json"
    resumes = load_json(resume_path)
    if not resumes:
        raise FileNotFoundError(f"Нет резюме для query={query}: {resume_path}")

    method = RANKING_METHOD
    use_e5 = method == "e5"
    model = SentenceTransformer(TRANSFORMER_MODELS[method])
    resume_texts = [_resume_text_for_embedding(r, use_e5) for r in resumes]
    resume_embeddings = model.encode(resume_texts, convert_to_tensor=True, normalize_embeddings=True)
    get_sim = make_similarity_getter(model, resume_embeddings, use_e5)
    pipeline_result = run_pipeline_for_vacancy(
        vacancy=vacancy,
        resumes=resumes,
        resume_ids=[r["id"] for r in resumes],
        get_similarity_scores=get_sim,
    )

    top_stage1 = pipeline_result.get("top_k_candidates") or []
    if not top_stage1:
        top_stage1 = (pipeline_result.get("candidates") or [])[:top_n]

    ce_name = CROSS_ENCODER_MODELS.get(RANKING_CE_MODEL, CROSS_ENCODER_MODELS["russian"])
    ce = CrossEncoder(ce_name)
    vac_entry = {
        "vacancy_id": vacancy.get("id"),
        "threshold": pipeline_result.get("threshold"),
        "candidates": top_stage1,
    }
    vacancies_by_id = {str(vacancy.get("id")): vacancy}
    resumes_by_id = {str(r.get("id")): r for r in resumes}
    pairs, selected = _build_pairs_for_vacancy(vac_entry, vacancies_by_id, resumes_by_id)

    if pairs:
        scores = ce.predict(pairs)
        for c, s in zip(selected, scores):
            c["rerank_score"] = float(s)
        selected.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        ranked = selected
    else:
        ranked = top_stage1

    display = resume_display_map(query)
    e5_rows, rerank_rows = _build_stage_lists(query, top_stage1, ranked)
    final = [
        _candidate_row(
            query,
            str(c.get("resume_id", "")),
            i,
            float(c.get("rerank_score", c.get("score_norm", 0))),
            c,
            display,
        )
        for i, c in enumerate(ranked[:top_n], start=1)
    ]
    return {
        "method": method,
        "ce_model": RANKING_CE_MODEL,
        "threshold": pipeline_result.get("threshold"),
        "e5_stage": e5_rows,
        "rerank_stage": rerank_rows,
        "final": final,
    }
