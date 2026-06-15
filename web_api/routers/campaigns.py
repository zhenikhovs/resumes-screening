import json
import logging
import secrets
import string
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from web_api.auth import hash_password
from web_api.database import SessionLocal, get_db
from web_api.deps import require_hr
from web_api.models import (
    Campaign,
    CampaignJob,
    CampaignStatus,
    Interview,
    InterviewStatus,
    Invitation,
    InvitationStatus,
    JobStatus,
    RankingResult,
    User,
    UserRole,
)
from web_api.schemas import (
    CampaignCreate,
    CampaignDetailOut,
    CampaignOut,
    CampaignResultsOut,
    InvitationCreate,
    InvitationOut,
    InterviewResultOut,
    JobOut,
    QuestionResultOut,
    RankingCandidateOut,
    RankingDebugOut,
    ScenarioInfoOut,
)
from services.interview.scenarios import question_dir
from services.preprocessing.resume_display import display_for_resume_id
from services.utils import load_json
from web_api.services.campaign_pipeline import ingest_from_hh, rank_campaign
from web_api.services.ranking_debug_api import ranking_debug_from_db_rows, ranking_debug_from_store
from web_api.services.ranking_debug_store import save_ranking_debug
from web_api.services.user_messages import to_user_message

logger = logging.getLogger(__name__)
from web_api.services.hh_fetch import fetch_vacancy_by_id, parse_vacancy_id
from web_api.services.interview_jobs import (
    friendly_processing_error,
    reprocess_interview_from_video_background,
)
from web_api.services.interview_runner import (
    copy_default_scenario,
    create_interview_workspace,
    new_interview_uid,
    save_scenario_upload,
    scenario_for_campaign,
    scenario_path_for_campaign,
)
from web_api.config import SMTP_HOST
from web_api.services.mailer import send_invitation_email

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _gen_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _password_for_candidate(db: Session, cand: User | None) -> tuple[str, bool]:
    """Пароль для письма и нужно ли обновить hash (только для нового аккаунта)."""
    if not cand:
        return _gen_password(), True
    prev = (
        db.query(Invitation)
        .filter(Invitation.candidate_user_id == cand.id)
        .order_by(Invitation.id.desc())
        .first()
    )
    if prev and prev.temp_password:
        return prev.temp_password, False
    return _gen_password(), True


def _campaign_to_out(c: Campaign) -> CampaignOut:
    return CampaignOut(
        id=c.id,
        title=c.title,
        hh_url=c.hh_url,
        hh_vacancy_id=c.hh_vacancy_id,
        query=c.query,
        search_text=c.search_text or "",
        status=c.status.value if hasattr(c.status, "value") else str(c.status),
        vacancy_title=c.vacancy_title,
        resumes_count=c.resumes_count or 0,
        demo_mode=bool(c.demo_mode),
        created_at=c.created_at,
    )


def _run_full_campaign_job(campaign_id: int, hh_vacancy_id: str, search_text: str, hh_raw: dict):
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return

        def set_status(st: CampaignStatus, err: str | None = None):
            campaign.status = st
            if err:
                job = (
                    db.query(CampaignJob)
                    .filter(CampaignJob.campaign_id == campaign_id)
                    .order_by(CampaignJob.id.desc())
                    .first()
                )
                if job:
                    job.error_message = err
                    job.status = JobStatus.failed
                    job.finished_at = datetime.utcnow()
            db.commit()

        set_status(CampaignStatus.collecting)
        info = ingest_from_hh(campaign_id, hh_vacancy_id, search_text, hh_raw)
        campaign.query = info["slug"]
        campaign.resumes_count = info.get("resumes_fetched", 0)
        campaign.demo_mode = info.get("demo_mode", False)
        scenario_path = copy_default_scenario(campaign.query)
        campaign.scenario_path = str(scenario_path)
        set_status(CampaignStatus.preparing)

        set_status(CampaignStatus.ranking)
        run = rank_campaign(campaign_id, hh_vacancy_id)
        save_ranking_debug(campaign_id, run)
        top = run.get("final") or []

        db.query(RankingResult).filter(RankingResult.campaign_id == campaign_id).delete()
        for row in top:
            db.add(
                RankingResult(
                    campaign_id=campaign_id,
                    resume_id=row["resume_id"],
                    rank=row["rank"],
                    score=row["score"],
                    title=row.get("position") or row.get("title"),
                    payload_json=json.dumps(row.get("payload", {}), ensure_ascii=False),
                )
            )
        campaign.status = CampaignStatus.ranked
        job = (
            db.query(CampaignJob)
            .filter(CampaignJob.campaign_id == campaign_id)
            .order_by(CampaignJob.id.desc())
            .first()
        )
        if job:
            job.status = JobStatus.done
            job.finished_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.exception("Campaign %s pipeline failed", campaign_id)
        if campaign := db.query(Campaign).filter(Campaign.id == campaign_id).first():
            campaign.status = CampaignStatus.failed
        job = (
            db.query(CampaignJob)
            .filter(CampaignJob.campaign_id == campaign_id)
            .order_by(CampaignJob.id.desc())
            .first()
        )
        if job:
            job.status = JobStatus.failed
            job.error_message = to_user_message(e)
            job.finished_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@router.post("", response_model=CampaignOut)
def create_campaign(
    body: CampaignCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    hr: User = Depends(require_hr),
):
    try:
        vacancy_id = parse_vacancy_id(body.hh_url)
        hh_raw = fetch_vacancy_by_id(vacancy_id)
    except Exception as e:
        logger.warning("Cannot load vacancy for new campaign: %s", e)
        raise HTTPException(status_code=400, detail=to_user_message(e)) from e

    search_text = body.search_text.strip()
    if not search_text:
        raise HTTPException(status_code=400, detail="Укажите поисковый запрос для резюме")

    campaign = Campaign(
        hr_user_id=hr.id,
        title=body.title or hh_raw.get("name", ""),
        hh_url=body.hh_url,
        hh_vacancy_id=vacancy_id,
        query="pending",
        search_text=search_text,
        vacancy_title=hh_raw.get("name"),
        status=CampaignStatus.collecting,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    campaign.query = f"camp_{campaign.id}"
    db.commit()

    job = CampaignJob(campaign_id=campaign.id, job_type="full_pipeline", status=JobStatus.queued)
    db.add(job)
    db.commit()

    background_tasks.add_task(_run_full_campaign_job, campaign.id, vacancy_id, search_text, hh_raw)
    return _campaign_to_out(campaign)


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db), hr: User = Depends(require_hr)):
    rows = (
        db.query(Campaign)
        .filter(Campaign.hr_user_id == hr.id)
        .order_by(Campaign.created_at.desc())
        .all()
    )
    return [_campaign_to_out(c) for c in rows]


@router.get("/{campaign_id}", response_model=CampaignDetailOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db), hr: User = Depends(require_hr)):
    c = _get_campaign_or_404(db, campaign_id, hr.id)
    jobs = (
        db.query(CampaignJob)
        .filter(CampaignJob.campaign_id == campaign_id)
        .order_by(CampaignJob.id.desc())
        .limit(5)
        .all()
    )
    try:
        path = scenario_path_for_campaign(c)
        sc = scenario_for_campaign(c)
        scenario = ScenarioInfoOut(path=str(path), loaded=True)
    except Exception:
        scenario = ScenarioInfoOut(path=c.scenario_path or "", loaded=False)

    return CampaignDetailOut(
        **_campaign_to_out(c).model_dump(),
        jobs=[JobOut.model_validate(j) for j in jobs],
        scenario=scenario,
    )


@router.get("/{campaign_id}/job", response_model=JobOut | None)
def get_latest_job(campaign_id: int, db: Session = Depends(get_db), hr: User = Depends(require_hr)):
    _ = _get_campaign_or_404(db, campaign_id, hr.id)
    job = (
        db.query(CampaignJob)
        .filter(CampaignJob.campaign_id == campaign_id)
        .order_by(CampaignJob.id.desc())
        .first()
    )
    return job


@router.get("/{campaign_id}/candidates", response_model=list[RankingCandidateOut])
def list_candidates(campaign_id: int, db: Session = Depends(get_db), hr: User = Depends(require_hr)):
    campaign = _get_campaign_or_404(db, campaign_id, hr.id)
    invitations = db.query(Invitation).filter(Invitation.campaign_id == campaign_id).all()
    invite_by_resume = {i.resume_id: i.email for i in invitations}
    rows = (
        db.query(RankingResult)
        .filter(RankingResult.campaign_id == campaign_id)
        .order_by(RankingResult.rank)
        .all()
    )
    query = campaign.query or f"camp_{campaign_id}"
    out = []
    for r in rows:
        disp = display_for_resume_id(query, r.resume_id, r.title)
        position = disp["position"]
        summary = disp["summary"]
        out.append(
            RankingCandidateOut(
                resume_id=r.resume_id,
                rank=r.rank,
                score=r.score,
                position=position,
                summary=summary,
                title=position,
                invited=r.resume_id in invite_by_resume,
                invited_email=invite_by_resume.get(r.resume_id),
            )
        )
    return out


@router.get("/{campaign_id}/ranking-debug", response_model=RankingDebugOut)
def campaign_ranking_debug(
    campaign_id: int, db: Session = Depends(get_db), hr: User = Depends(require_hr)
):
    campaign = _get_campaign_or_404(db, campaign_id, hr.id)
    stored = ranking_debug_from_store(campaign_id)
    if stored:
        return stored
    rows = (
        db.query(RankingResult)
        .filter(RankingResult.campaign_id == campaign_id)
        .order_by(RankingResult.rank)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Ранжирование ещё не выполнено")
    query = campaign.query or f"camp_{campaign_id}"
    return ranking_debug_from_db_rows(query, rows)


@router.post("/{campaign_id}/scenario")
async def upload_scenario(
    campaign_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    hr: User = Depends(require_hr),
):
    c = _get_campaign_or_404(db, campaign_id, hr.id)
    content = await file.read()
    try:
        path = save_scenario_upload(campaign_id, c.query, content)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    c.scenario_path = str(path)
    db.commit()
    sc = scenario_for_campaign(c)
    return {"ok": True, "questions_count": len(sc.get("questions", []))}


@router.post("/{campaign_id}/invitations", response_model=list[InvitationOut])
def send_invitations(
    campaign_id: int,
    body: InvitationCreate,
    db: Session = Depends(get_db),
    hr: User = Depends(require_hr),
):
    campaign = _get_campaign_or_404(db, campaign_id, hr.id)
    if campaign.status != CampaignStatus.ranked:
        raise HTTPException(status_code=400, detail="Дождитесь завершения ранжирования")

    if len(body.resume_ids) != len(body.emails):
        raise HTTPException(status_code=400, detail="resume_ids и emails должны быть одинаковой длины")

    scenario_for_campaign(campaign)
    created = []

    for resume_id, email in zip(body.resume_ids, body.emails):
        existing = (
            db.query(Invitation)
            .filter(Invitation.campaign_id == campaign_id, Invitation.resume_id == resume_id)
            .first()
        )
        if existing:
            if not existing.access_token:
                existing.access_token = secrets.token_urlsafe(32)
            existing.email = email
            temp_pass = existing.temp_password
            invite_path = f"/i/{existing.access_token}"
            send_invitation_email(
                email,
                temp_pass,
                campaign.title or campaign.vacancy_title or "Вакансия",
                campaign_id,
                invite_path,
            )
            created.append(existing)
            continue

        other = db.query(User).filter(User.email == email).first()
        if other and other.role != UserRole.candidate:
            raise HTTPException(status_code=400, detail=f"Email {email} уже используется")
        cand = other
        temp_pass, set_hash = _password_for_candidate(db, cand)
        if not cand:
            cand = User(
                email=email,
                password_hash=hash_password(temp_pass),
                role=UserRole.candidate,
                full_name=f"Candidate {resume_id}",
            )
            db.add(cand)
            db.flush()
        elif set_hash:
            cand.password_hash = hash_password(temp_pass)

        interview_uid = new_interview_uid()
        create_interview_workspace(interview_uid, resume_id, campaign.query)
        access_token = secrets.token_urlsafe(32)

        inv = Invitation(
            campaign_id=campaign_id,
            resume_id=resume_id,
            email=email,
            access_token=access_token,
            temp_password=temp_pass,
            candidate_user_id=cand.id,
            status=InvitationStatus.sent,
        )
        db.add(inv)
        db.flush()

        db.add(
            Interview(
                invitation_id=inv.id,
                campaign_id=campaign_id,
                interview_uid=interview_uid,
                status=InterviewStatus.pending,
            )
        )
        db.flush()

        invite_path = f"/i/{access_token}"
        send_invitation_email(
            email,
            temp_pass,
            campaign.title or campaign.vacancy_title or "Вакансия",
            campaign_id,
            invite_path,
        )
        created.append(inv)

    db.commit()
    out = []
    for inv in created:
        db.refresh(inv)
        out.append(
            InvitationOut(
                id=inv.id,
                resume_id=inv.resume_id,
                email=inv.email,
                temp_password=inv.temp_password,
                invite_path=f"/i/{inv.access_token}" if inv.access_token else None,
                status=inv.status.value,
                email_sent=bool(SMTP_HOST),
            )
        )
    return out


# SMTP check for response flag

def _interview_error_message(iv: Interview) -> str | None:
    if not iv.summary_json:
        return None
    try:
        data = json.loads(iv.summary_json)
    except json.JSONDecodeError:
        return None
    if data.get("error_hr"):
        return data["error_hr"]
    if data.get("error"):
        return friendly_processing_error(str(data["error"]))
    return None


def _transcript_for_question(interview_uid: str, question_id: str) -> str | None:
    path = question_dir(interview_uid, question_id) / "transcript.json"
    if not path.exists():
        return None
    try:
        data = load_json(path)
        text = (data.get("text") or "").strip()
        return text or None
    except Exception:
        return None


def _question_row(
    question_id: str,
    question: str,
    score: int | None,
    feedback: str | None,
    interview_uid: str,
    transcript_from_summary: str | None = None,
) -> QuestionResultOut:
    transcript = (transcript_from_summary or "").strip() or _transcript_for_question(
        interview_uid, question_id
    )
    return QuestionResultOut(
        question_id=question_id,
        question=question,
        score=score,
        feedback=feedback,
        transcript=transcript,
    )


def _question_results_for_interview(iv: Interview, campaign: Campaign) -> list[QuestionResultOut]:
    stored: list[dict] = []
    if iv.summary_json:
        try:
            data = json.loads(iv.summary_json)
            stored = data.get("questions") or []
        except json.JSONDecodeError:
            stored = []

    if stored:
        return [
            _question_row(
                q.get("question_id", ""),
                q.get("question", ""),
                q.get("score"),
                q.get("feedback") or q.get("summary"),  # summary — старые файлы
                iv.interview_uid,
                q.get("transcript"),
            )
            for q in stored
        ]

    try:
        scenario = scenario_for_campaign(campaign)
    except Exception:
        return []

    out: list[QuestionResultOut] = []
    for q in scenario.get("questions", []):
        qid = q.get("question_id", "")
        eval_path = question_dir(iv.interview_uid, qid) / "evaluation.json"
        if not eval_path.exists():
            continue
        ev = load_json(eval_path)
        out.append(
            _question_row(
                qid,
                q.get("question", ""),
                ev.get("score"),
                ev.get("feedback") or ev.get("summary"),
                iv.interview_uid,
            )
        )
    return out


@router.get("/{campaign_id}/results", response_model=CampaignResultsOut)
def campaign_results(campaign_id: int, db: Session = Depends(get_db), hr: User = Depends(require_hr)):
    campaign = _get_campaign_or_404(db, campaign_id, hr.id)
    interviews = db.query(Interview).filter(Interview.campaign_id == campaign_id).all()
    out = []
    for iv in interviews:
        inv = db.query(Invitation).filter(Invitation.id == iv.invitation_id).first()
        questions = _question_results_for_interview(iv, campaign)
        out.append(
            InterviewResultOut(
                interview_id=iv.id,
                candidate_email=inv.email if inv else "",
                resume_id=inv.resume_id if inv else "",
                status=iv.status.value,
                score_avg=iv.score_avg,
                approved=iv.approved,
                error_message=_interview_error_message(iv),
                questions=questions,
            )
        )
    return CampaignResultsOut(campaign_id=campaign_id, interviews=out)


@router.post("/{campaign_id}/interviews/{interview_id}/reprocess")
def reprocess_interview(
    campaign_id: int,
    interview_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    hr: User = Depends(require_hr),
):
    _ = _get_campaign_or_404(db, campaign_id, hr.id)
    iv = (
        db.query(Interview)
        .filter(Interview.id == interview_id, Interview.campaign_id == campaign_id)
        .first()
    )
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")
    if iv.status == InterviewStatus.processing:
        raise HTTPException(status_code=400, detail="Обработка уже идёт")
    background_tasks.add_task(reprocess_interview_from_video_background, iv.id)
    return {
        "ok": True,
        "message": "Повторная обработка: аудио и транскрипт с видео, затем оценка",
    }


def _get_campaign_or_404(db: Session, campaign_id: int, hr_id: int) -> Campaign:
    c = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.hr_user_id == hr_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c
