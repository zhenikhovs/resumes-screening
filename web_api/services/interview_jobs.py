"""Фоновая обработка видео-собеседования (ASR + оценка)."""
import json
from datetime import datetime

from web_api.database import SessionLocal
from web_api.models import Campaign, Interview, InterviewStatus
import logging

from web_api.services.interview_runner import (
    run_interview_processing,
    run_interview_reprocess_from_video,
    scenario_for_campaign,
    transcribe_after_upload,
)

logger = logging.getLogger(__name__)


def friendly_processing_error(message: str) -> str:
    msg = (message or "").strip()
    if "CERTIFICATE_VERIFY_FAILED" in msg or "certificate verify failed" in msg.lower():
        return (
            "Не удалось загрузить модель распознавания речи (ошибка SSL-сертификата на Mac). "
            "В терминале: pip install certifi, перезапустите API. "
            "Или выполните «Install Certificates.command» из папки Python."
        )
    if "GROQ_API_KEY" in msg or "groq" in msg.lower():
        return "Не задан или неверный GROQ_API_KEY в .env."
    if "ffmpeg" in msg.lower():
        return "Не найден ffmpeg — установите: brew install ffmpeg"
    return msg[:500] if msg else "Неизвестная ошибка обработки"


def transcribe_upload_background(interview_uid: str, question_id: str) -> None:
    try:
        transcribe_after_upload(interview_uid, question_id)
    except Exception:
        logger.exception("ASR после загрузки %s/%s", interview_uid, question_id)


def reprocess_interview_from_video_background(interview_db_id: int) -> None:
    process_interview_background(interview_db_id, from_video=True)


def process_interview_background(interview_db_id: int, *, from_video: bool = False) -> None:
    db = SessionLocal()
    iv = None
    try:
        iv = db.query(Interview).filter(Interview.id == interview_db_id).first()
        if not iv:
            return
        campaign = db.query(Campaign).filter(Campaign.id == iv.campaign_id).first()
        scenario = scenario_for_campaign(campaign)
        qids = [q["question_id"] for q in scenario["questions"]]

        iv.status = InterviewStatus.processing
        iv.summary_json = None
        db.commit()

        if from_video:
            summary = run_interview_reprocess_from_video(iv.interview_uid, campaign, qids)
        else:
            summary = run_interview_processing(iv.interview_uid, campaign, qids)
        iv.status = InterviewStatus.completed
        iv.score_avg = summary.get("interview_score_avg")
        iv.approved = summary.get("approved")
        iv.summary_json = json.dumps(summary, ensure_ascii=False)
        iv.completed_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        if iv := db.query(Interview).filter(Interview.id == interview_db_id).first():
            iv.status = InterviewStatus.failed
            iv.summary_json = json.dumps(
                {"error": str(e), "error_hr": friendly_processing_error(str(e))},
                ensure_ascii=False,
            )
            db.commit()
    finally:
        db.close()
