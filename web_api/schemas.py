from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InterviewChoiceOut(BaseModel):
    interview_id: int
    campaign_title: str
    entry_path: str


class AuthLoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    full_name: str | None = None

    class Config:
        from_attributes = True


class CampaignCreate(BaseModel):
    hh_url: str = Field(..., description="Ссылка на вакансию hh.ru")
    search_text: str = Field(..., description="Поисковый запрос для резюме на hh.ru")
    title: str = ""


class CampaignOut(BaseModel):
    id: int
    title: str
    hh_url: str
    hh_vacancy_id: str
    query: str
    search_text: str
    status: str
    vacancy_title: str | None
    resumes_count: int = 0
    demo_mode: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: int
    job_type: str
    status: str
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True


class ScenarioInfoOut(BaseModel):
    path: str
    loaded: bool = True


class CampaignDetailOut(CampaignOut):
    jobs: list[JobOut] = []
    scenario: ScenarioInfoOut | None = None


class RankingCandidateOut(BaseModel):
    resume_id: str
    rank: int
    position: str | None = None
    summary: str | None = None
    title: str | None = None  # то же, что position (совместимость)
    invited: bool = False
    invited_email: str | None = None


class RankingStageRowOut(BaseModel):
    rank: int
    resume_id: str
    position: str | None = None
    summary: str | None = None
    similarity_score: float | None = None
    experience_match: int | None = None
    final_score: float | None = None
    score_norm: float | None = None
    rerank_score: float | None = None


class RankingDebugOut(BaseModel):
    method: str = "e5"
    ce_model: str = "russian"
    threshold: float | None = None
    e5_stage: list[RankingStageRowOut] = []
    rerank_stage: list[RankingStageRowOut] = []
    note: str | None = None


class InvitationCreate(BaseModel):
    resume_ids: list[str]
    emails: list[EmailStr]


class InvitationOut(BaseModel):
    id: int
    resume_id: str
    email: str
    temp_password: str
    invite_path: str | None = None
    status: str
    email_sent: bool = False

    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    question_id: str
    question: str
    order: int


class InterviewSessionOut(BaseModel):
    interview_id: int
    interview_uid: str
    status: str
    campaign_title: str
    vacancy_title: str | None
    questions: list[QuestionOut]
    current_index: int
    total_questions: int


class InterviewCompleteResponse(BaseModel):
    status: str
    message: str


class QuestionResultOut(BaseModel):
    question_id: str
    question: str
    score: int | None
    feedback: str | None = None
    transcript: str | None = None


class InterviewResultOut(BaseModel):
    interview_id: int
    candidate_email: str
    resume_id: str
    status: str
    score_avg: float | None
    approved: bool | None
    error_message: str | None = None
    questions: list[QuestionResultOut]


class CampaignResultsOut(BaseModel):
    campaign_id: int
    interviews: list[InterviewResultOut]
