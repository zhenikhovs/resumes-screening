"""FastAPI: веб-приложение AI Resume Screening."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web_api.config import CORS_ORIGINS
from web_api.database import Base, SessionLocal, engine
from web_api.migrate_db import migrate_sqlite
from web_api.routers import auth, campaigns, interviews
from web_api.seed import seed_hr_user


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_sqlite()
    db = SessionLocal()
    try:
        seed_hr_user(db)
    finally:
        db.close()
    yield


app = FastAPI(title="AI Resume Screening API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(campaigns.router)
app.include_router(interviews.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
