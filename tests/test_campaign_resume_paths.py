"""Проверка: веб-кампания не рассинхронизирует пути к резюме."""
from pathlib import Path

from web_api.services.campaign_pipeline import _full_resumes_path, _slug


def test_full_resumes_path_matches_fetch_suffix():
    slug = _slug(42)
    suffix = slug.replace(" ", "_")
    path = _full_resumes_path(slug)
    assert path.name == f"resumes_{suffix}.json"
    assert path.parent.name == "resumes"


def test_slug_format():
    assert _slug(1) == "camp_1"
