from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from web_api.auth import create_access_token, verify_password
from web_api.database import get_db
from web_api.deps import get_current_user, require_candidate
from web_api.models import Campaign, Interview, InterviewStatus, Invitation, User, UserRole
from web_api.schemas import AuthLoginOut, InterviewChoiceOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])

_OPEN_INTERVIEW_STATUSES = (
    InterviewStatus.pending,
    InterviewStatus.in_progress,
)


def _active_interviews(db: Session, user_id: int) -> list[Interview]:
    return (
        db.query(Interview)
        .join(Invitation, Invitation.id == Interview.invitation_id)
        .filter(
            Invitation.candidate_user_id == user_id,
            Interview.status.in_(_OPEN_INTERVIEW_STATUSES),
        )
        .order_by(Interview.id.desc())
        .all()
    )


def _interview_choices(db: Session, interviews: list[Interview]) -> list[InterviewChoiceOut]:
    choices: list[InterviewChoiceOut] = []
    for iv in interviews:
        inv = db.query(Invitation).filter(Invitation.id == iv.invitation_id).first()
        if not inv or not inv.access_token:
            continue
        camp = db.query(Campaign).filter(Campaign.id == iv.campaign_id).first()
        title = (camp.vacancy_title or "Вакансия") if camp else "Вакансия"
        choices.append(
            InterviewChoiceOut(
                interview_id=iv.id,
                campaign_title=title,
                entry_path=f"/i/{inv.access_token}",
            )
        )
    return choices


@router.post("/login", response_model=AuthLoginOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Только вход (сессия). Какое собеседование — по ссылке /i/... после входа."""
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.email, user.role.value)
    return AuthLoginOut(access_token=token)


@router.get("/interviews", response_model=list[InterviewChoiceOut])
def list_my_interviews(
    db: Session = Depends(get_db),
    user: User = Depends(require_candidate),
):
    """Активные собеседования — те же ссылки, что в письме."""
    interviews = _active_interviews(db, user.id)
    return _interview_choices(db, interviews)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
