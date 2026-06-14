from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.mom import MOM
from app.routers import auth, meeting, transcription, mom, download
from app.database import engine, Base

app = FastAPI(
    title="AI Meeting Platform",
    description="Backend API for AI Meeting System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)
app.include_router(
    meeting.router,
    prefix="/meeting",
    tags=["Meeting"]
)
app.include_router(
    transcription.router,
    prefix="/transcription",
    tags=["Transcription"]
)
app.include_router(
    mom.router,
    prefix="/mom",
    tags=["MOM"]
)
app.include_router(
    download.router,
    prefix="/download",
    tags=["Download"]
)

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {
        "message": "AI Meeting Platform API is running!"
    }