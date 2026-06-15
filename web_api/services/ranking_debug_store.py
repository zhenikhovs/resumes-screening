"""Сохранение этапов E5 и rerank для отладки в UI."""
import json
from pathlib import Path
from typing import Any

from services.utils import load_json, save_json
from web_api.config import CAMPAIGNS_DATA_DIR


def _path(campaign_id: int) -> Path:
    CAMPAIGNS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return CAMPAIGNS_DATA_DIR / f"ranking_debug_camp_{campaign_id}.json"


def save_ranking_debug(campaign_id: int, data: dict[str, Any]) -> None:
    save_json(_path(campaign_id), data)


def load_ranking_debug(campaign_id: int) -> dict[str, Any] | None:
    p = _path(campaign_id)
    if not p.exists():
        return None
    return load_json(p)
