"""Ответ API с этапами E5 / rerank для HR."""
from __future__ import annotations

import json

from services.preprocessing.resume_display import display_for_resume_id
from web_api.models import RankingResult
from web_api.schemas import RankingDebugOut, RankingStageRowOut
from web_api.services.ranking_debug_store import load_ranking_debug


def _row_from_payload(rank: int, resume_id: str, query: str, payload: dict, title: str | None) -> RankingStageRowOut:
    disp = display_for_resume_id(query, resume_id, title)
    return RankingStageRowOut(
        rank=rank,
        resume_id=resume_id,
        position=disp["position"],
        summary=disp["summary"],
        similarity_score=payload.get("similarity_score"),
        experience_match=payload.get("experience_match"),
        final_score=payload.get("final_score"),
        score_norm=payload.get("score_norm"),
        rerank_score=payload.get("rerank_score"),
    )


def ranking_debug_from_store(campaign_id: int) -> RankingDebugOut | None:
    raw = load_ranking_debug(campaign_id)
    if not raw:
        return None
    return RankingDebugOut(
        method=raw.get("method", "e5"),
        ce_model=raw.get("ce_model", "russian"),
        threshold=raw.get("threshold"),
        e5_stage=[RankingStageRowOut(**r) for r in raw.get("e5_stage", [])],
        rerank_stage=[RankingStageRowOut(**r) for r in raw.get("rerank_stage", [])],
        note=raw.get("note"),
    )


def ranking_debug_from_db_rows(
    query: str,
    rows: list[RankingResult],
) -> RankingDebugOut:
    payloads = []
    for r in rows:
        pl = {}
        if r.payload_json:
            try:
                pl = json.loads(r.payload_json)
            except json.JSONDecodeError:
                pl = {}
        payloads.append((r, pl))

    e5_sorted = sorted(
        payloads,
        key=lambda x: x[1].get("score_norm", 0),
        reverse=True,
    )
    rerank_sorted = sorted(
        payloads,
        key=lambda x: x[1].get("rerank_score", x[1].get("score_norm", 0)),
        reverse=True,
    )
    e5_stage = [
        _row_from_payload(i, r.resume_id, query, pl, r.title)
        for i, (r, pl) in enumerate(e5_sorted, start=1)
    ]
    rerank_stage = [
        _row_from_payload(i, r.resume_id, query, pl, r.title)
        for i, (r, pl) in enumerate(rerank_sorted, start=1)
    ]
    return RankingDebugOut(
        method="e5",
        ce_model="russian",
        threshold=None,
        e5_stage=e5_stage,
        rerank_stage=rerank_stage,
        note=(
            "Восстановлено из сохранённого топа (полный список E5 до rerank доступен "
            "после нового подбора). Порядок E5 — по score_norm; итоговый топ — по rerank_score."
        ),
    )
