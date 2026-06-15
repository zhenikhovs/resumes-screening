from sqlalchemy.orm import Session

from web_api.auth import hash_password
from web_api.config import WEB_HR_EMAIL, WEB_HR_PASSWORD
from web_api.models import User, UserRole


def seed_hr_user(db: Session) -> None:
    existing = db.query(User).filter(User.email == WEB_HR_EMAIL).first()
    if existing:
        return
    db.add(
        User(
            email=WEB_HR_EMAIL,
            password_hash=hash_password(WEB_HR_PASSWORD),
            role=UserRole.hr,
            full_name="HR Admin",
        )
    )
    db.commit()
    print(f"[seed] HR user: {WEB_HR_EMAIL}")
