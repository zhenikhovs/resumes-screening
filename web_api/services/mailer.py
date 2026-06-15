"""Отправка приглашений кандидатам (SMTP или запись в лог)."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from web_api.config import (
    APP_PUBLIC_URL,
    CAMPAIGNS_DATA_DIR,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)


def send_invitation_email(
    to_email: str,
    temp_password: str,
    campaign_title: str,
    campaign_id: int,
    invite_path: str,
) -> bool:
    invite_url = f"{APP_PUBLIC_URL.rstrip('/')}{invite_path}"
    subject = f"Приглашение на видео-собеседование — {campaign_title}"
    body = f"""Здравствуйте!

Вас приглашают пройти видео-собеседование по вакансии «{campaign_title}».

Ссылка для входа:
{invite_url}

Email: {to_email}
Пароль: {temp_password}

С уважением,
Служба подбора персонала
"""
    log_dir = CAMPAIGNS_DATA_DIR / str(campaign_id)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "invitation_emails.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n---\nTo: {to_email}\n{body}\n")

    if not SMTP_HOST:
        return False

    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
    return True
