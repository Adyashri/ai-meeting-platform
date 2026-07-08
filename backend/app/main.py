from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import socketio

from app.config import settings
from app.database import Base, engine
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcript import Transcript
from app.models.mom import MOM
from app.routers import auth, meeting, transcription, mom, download
from app.services.socket_service import sio
import threading
from app.celery_app import celery_app

# Celery worker ko background thread mein start karo (free tier ke liye)
def start_celery_worker():
    celery_app.worker_main(
        argv=["worker", "--loglevel=info", "--pool=solo"]
    )

worker_thread = threading.Thread(target=start_celery_worker, daemon=True)
worker_thread.start()

# FastAPI app
fastapi_app = FastAPI(
    title="AI Meeting Platform",
    description="Backend API for AI Meeting System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Session middleware — Google OAuth ke liye
fastapi_app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY
)

# CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://ai-meeting-platform-rqjq-seven.vercel.app",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
fastapi_app.include_router(auth.router,          prefix="/auth",          tags=["Authentication"])
fastapi_app.include_router(meeting.router,        prefix="/meeting",       tags=["Meeting"])
fastapi_app.include_router(transcription.router,  prefix="/transcription", tags=["Transcription"])
fastapi_app.include_router(mom.router,            prefix="/mom",           tags=["MOM"])
fastapi_app.include_router(download.router,       prefix="/download",      tags=["Download"])

# Database tables
Base.metadata.create_all(bind=engine)

@fastapi_app.get("/")
def root():
    return {"message": "AI Meeting Platform API is running!", "docs": "/docs", "status": "ok"}

@fastapi_app.get("/health")
def health_check():
    return {"status": "ok"}

# Socket.io + FastAPI combine karo
socket_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# Main app — uvicorn ye chalayega
app = socket_app