"""Доступ кандидата к собеседованию по ссылке из письма (/i/{access_token})."""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from web_api.database import get_db
from web_api.deps import get_current_user
from web_api.models import Interview, Invitation, User


def get_interview_by_invite(
    access_token: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Interview:
    inv = db.query(Invitation).filter(Invitation.access_token == access_token).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ссылка не найдена")
    if inv.candidate_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этому собеседованию",
        )
    iv = db.query(Interview).filter(Interview.invitation_id == inv.id).first()
    if not iv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Собеседование не найдено")
    return iv
