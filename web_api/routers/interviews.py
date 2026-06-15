import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from web_api.database import get_db
from web_api.deps import require_candidate
from web_api.deps_interview import get_interview_by_invite
from web_api.models import Campaign, Interview, InterviewStatus
from web_api.schemas import (
    InterviewCompleteResponse,
    InterviewSessionOut,
    QuestionOut,
)
from web_api.services.interview_jobs import process_interview_background, transcribe_upload_background
from web_api.services.interview_runner import scenario_for_campaign, sync_uploaded_video

router = APIRouter(prefix="/api/i", tags=["interviews"])


@router.get("/{access_token}", response_model=InterviewSessionOut)
def get_interview_session(
    access_token: str,
    db: Session = Depends(get_db),
    _user=Depends(require_candidate),
    iv: Interview = Depends(get_interview_by_invite),
):
    campaign = db.query(Campaign).filter(Campaign.id == iv.campaign_id).first()
    scenario = scenario_for_campaign(campaign)

    from services.interview.scenarios import question_dir

    answered = 0
    for q in scenario["questions"]:
        qid = q["question_id"]
        if (question_dir(iv.interview_uid, qid) / "evaluation.json").exists():
            answered += 1
        elif list((question_dir(iv.interview_uid, qid)).glob("raw.*")):
            answered += 1

    if iv.status == InterviewStatus.pending:
        iv.status = InterviewStatus.in_progress
        db.commit()

    questions = [
        QuestionOut(question_id=q["question_id"], question=q["question"], order=i)
        for i, q in enumerate(scenario["questions"])
    ]

    return InterviewSessionOut(
        interview_id=iv.id,
        interview_uid=iv.interview_uid,
        status=iv.status.value,
        campaign_title="",
        vacancy_title=(campaign.vacancy_title or None) if campaign else None,
        questions=questions,
        current_index=min(answered, len(questions)),
        total_questions=len(questions),
    )


@router.post("/{access_token}/questions/{question_id}/video")
async def upload_video(
    access_token: str,
    question_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user=Depends(require_candidate),
    iv: Interview = Depends(get_interview_by_invite),
):
    if iv.status not in (InterviewStatus.pending, InterviewStatus.in_progress):
        raise HTTPException(status_code=400, detail="Interview not accepting uploads")

    suffix = Path(file.filename or "video.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    sync_uploaded_video(iv.interview_uid, question_id, tmp_path)
    tmp_path.unlink(missing_ok=True)
    iv.status = InterviewStatus.in_progress
    db.commit()
    background_tasks.add_task(transcribe_upload_background, iv.interview_uid, question_id)
    return {"ok": True, "question_id": question_id}


@router.post("/{access_token}/complete", response_model=InterviewCompleteResponse)
def complete_interview(
    access_token: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user=Depends(require_candidate),
    iv: Interview = Depends(get_interview_by_invite),
):
    campaign = db.query(Campaign).filter(Campaign.id == iv.campaign_id).first()
    scenario = scenario_for_campaign(campaign)

    from services.interview.scenarios import question_dir

    for q in scenario["questions"]:
        qdir = question_dir(iv.interview_uid, q["question_id"])
        if not list(qdir.glob("raw.*")):
            raise HTTPException(
                status_code=400,
                detail=f"Нет видео для вопроса {q['question_id']}",
            )

    background_tasks.add_task(process_interview_background, iv.id)
    return InterviewCompleteResponse(
        status="processing",
        message=(
            "Спасибо! Собеседование завершено. Ваши ответы переданы специалистам. "
            "При положительном решении с вами свяжутся."
        ),
    )
