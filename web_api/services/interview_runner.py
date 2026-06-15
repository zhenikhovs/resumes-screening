"""Фоновая обработка интервью (ASR + Groq) и сценарии."""
import json
import shutil
import uuid
from pathlib import Path

from config.interview_config import INTERVIEW_PASS_THRESHOLD
from services.interview.pipeline import finalize_interview, init_interview, process_question
from services.interview.scenarios import load_scenario
from services.utils import load_json, save_json
from web_api.config import SCENARIOS_DIR, UPLOAD_DIR


def scenario_path_for_campaign(campaign) -> Path:
    if campaign.scenario_path:
        p = Path(campaign.scenario_path)
        if p.exists():
            return p
    return SCENARIOS_DIR / f"{campaign.query}.json"


def _normalize_scenario_file(data: dict) -> dict:
    """В файле хранятся только вопросы; порог и query — из кода/кампании."""
    questions = data.get("questions")
    if not questions:
        raise ValueError("В файле должно быть поле questions (массив вопросов)")
    return {"questions": questions}


def scenario_for_campaign(campaign) -> dict:
    path = scenario_path_for_campaign(campaign)
    if not path.exists():
        raise FileNotFoundError(f"Сценарий не найден: {path}. Загрузите файл вопросов в кампании.")
    raw = load_json(path)
    if not isinstance(raw, dict):
        raise ValueError(f"Некорректный сценарий: {path}")
    data = _normalize_scenario_file(raw)
    data["query"] = campaign.query
    data["pass_threshold"] = INTERVIEW_PASS_THRESHOLD
    return data


def save_scenario_upload(campaign_id: int, query: str, content: bytes) -> Path:
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    path = SCENARIOS_DIR / f"{query}.json"
    raw = json.loads(content.decode("utf-8"))
    save_json(path, _normalize_scenario_file(raw))
    return path


def copy_default_scenario(query: str, fallback: str = "backend_developer") -> Path:
    """Копирует вопросы из шаблона для новой кампании (только questions)."""
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    dst = SCENARIOS_DIR / f"{query}.json"
    src = SCENARIOS_DIR / f"{fallback.replace(' ', '_')}.json"
    if not src.exists():
        src = SCENARIOS_DIR / "backend_developer.json"
    if src.exists() and not dst.exists():
        src_data = load_json(src) or {}
        save_json(dst, _normalize_scenario_file(src_data))
    return dst


def create_interview_workspace(interview_uid: str, candidate_id: str, query: str) -> None:
    init_interview(interview_uid, candidate_id, query)


def sync_uploaded_video(interview_uid: str, question_id: str, uploaded_path: Path) -> Path:
    from services.interview.scenarios import question_dir

    dest_dir = question_dir(interview_uid, question_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"raw{uploaded_path.suffix.lower()}"
    shutil.copy2(uploaded_path, dest)
    return dest


def _question_paths(interview_uid: str, question_id: str) -> tuple[Path, Path, Path]:
    qdir = UPLOAD_DIR / interview_uid / "questions" / question_id
    return qdir, qdir / "audio_16k.wav", qdir / "transcript.json"


def transcribe_after_upload(interview_uid: str, question_id: str) -> None:
    """Сразу после загрузки видео: ffmpeg → Whisper (без оценки Groq)."""
    qdir, _, _ = _question_paths(interview_uid, question_id)
    raw_files = list(qdir.glob("raw.*"))
    if not raw_files:
        return
    process_question(interview_uid, question_id, raw_files[0], skip_evaluate=True)


def run_interview_processing(interview_uid: str, campaign, question_ids: list[str]) -> dict:
    """После «Завершить»: ASR при необходимости, затем оценка (если транскрипт уже есть — только Groq)."""
    for qid in question_ids:
        qdir, audio_path, transcript_path = _question_paths(interview_uid, qid)
        raw_files = list(qdir.glob("raw.*"))
        if not raw_files:
            raise FileNotFoundError(f"Нет видео для вопроса {qid}")
        if not transcript_path.exists():
            process_question(interview_uid, qid, raw_files[0], skip_evaluate=True)
        process_question(
            interview_uid,
            qid,
            raw_files[0],
            skip_extract=True,
            skip_transcribe=True,
            skip_evaluate=False,
        )
    return finalize_interview(interview_uid)


def run_interview_reprocess_from_video(
    interview_uid: str, campaign, question_ids: list[str]
) -> dict:
    """Повтор с нуля: raw.webm → аудио → Whisper → оценка Groq по каждому вопросу."""
    for qid in question_ids:
        qdir, _, _ = _question_paths(interview_uid, qid)
        raw_files = list(qdir.glob("raw.*"))
        if not raw_files:
            raise FileNotFoundError(f"Нет видео для вопроса {qid}")
        process_question(interview_uid, qid, raw_files[0])
    return finalize_interview(interview_uid)


def new_interview_uid() -> str:
    return f"int_{uuid.uuid4().hex[:12]}"
