"""Миграции SQLite без Alembic."""
import secrets

from sqlalchemy import inspect, text

from web_api.database import engine


def migrate_sqlite() -> None:
    migrate_campaign_columns()
    migrate_invitation_access_tokens()


def migrate_campaign_columns() -> None:
    insp = inspect(engine)
    if "campaigns" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("campaigns")}
    alters = []
    if "search_text" not in existing:
        alters.append("ALTER TABLE campaigns ADD COLUMN search_text VARCHAR(512) DEFAULT ''")
    if "resumes_count" not in existing:
        alters.append("ALTER TABLE campaigns ADD COLUMN resumes_count INTEGER DEFAULT 0")
    if "demo_mode" not in existing:
        alters.append("ALTER TABLE campaigns ADD COLUMN demo_mode BOOLEAN DEFAULT 0")
    if not alters:
        return
    with engine.begin() as conn:
        for sql in alters:
            conn.execute(text(sql))


def migrate_invitation_access_tokens() -> None:
    insp = inspect(engine)
    if "invitations" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("invitations")}
    with engine.begin() as conn:
        if "access_token" not in cols:
            conn.execute(text("ALTER TABLE invitations ADD COLUMN access_token VARCHAR(64)"))
        rows = conn.execute(
            text("SELECT id FROM invitations WHERE access_token IS NULL OR access_token = ''")
        ).fetchall()
        for (inv_id,) in rows:
            token = secrets.token_urlsafe(32)
            conn.execute(
                text("UPDATE invitations SET access_token = :t WHERE id = :id"),
                {"t": token, "id": inv_id},
            )
