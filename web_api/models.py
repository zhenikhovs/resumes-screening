import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from web_api.database import Base


class UserRole(str, enum.Enum):
    hr = "hr"
    candidate = "candidate"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    collecting = "collecting"
    preparing = "preparing"
    ranking = "ranking"
    ranked = "ranked"
    failed = "failed"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class InvitationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    accepted = "accepted"


class InterviewStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="hr_user")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="candidate_user")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hr_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(512), default="")
    hh_url: Mapped[str] = mapped_column(String(1024))
    hh_vacancy_id: Mapped[str] = mapped_column(String(64), index=True)
    query: Mapped[str] = mapped_column(String(128), index=True)
    search_text: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.draft)
    vacancy_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    scenario_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    resumes_count: Mapped[int] = mapped_column(Integer, default=0)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    hr_user: Mapped["User"] = relationship(back_populates="campaigns")
    jobs: Mapped[list["CampaignJob"]] = relationship(back_populates="campaign")
    ranking_results: Mapped[list["RankingResult"]] = relationship(back_populates="campaign")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="campaign")


class CampaignJob(Base):
    __tablename__ = "campaign_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    job_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="jobs")


class RankingResult(Base):
    __tablename__ = "ranking_results"
    __table_args__ = (UniqueConstraint("campaign_id", "resume_id", name="uq_campaign_resume"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    resume_id: Mapped[str] = mapped_column(String(64))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="ranking_results")


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    resume_id: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(255))
    access_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    temp_password: Mapped[str] = mapped_column(String(128))
    candidate_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus), default=InvitationStatus.sent
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    campaign: Mapped["Campaign"] = relationship(back_populates="invitations")
    candidate_user: Mapped["User | None"] = relationship(back_populates="invitations")
    interview: Mapped["Interview | None"] = relationship(back_populates="invitation", uselist=False)


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invitation_id: Mapped[int] = mapped_column(ForeignKey("invitations.id"), unique=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    interview_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus), default=InterviewStatus.pending
    )
    score_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    invitation: Mapped["Invitation"] = relationship(back_populates="interview")
