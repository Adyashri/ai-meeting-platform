from sqlalchemy import Column, String, Float, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base
import uuid

def _uuid():
    return str(uuid.uuid4())

class Transcript(Base):
    __tablename__ = "transcripts"
    __table_args__ = {"extend_existing": True}

    id           = Column(String, primary_key=True, default=_uuid)
    meeting_id   = Column(String, nullable=True)
    speaker_name = Column(String, nullable=True)
    text         = Column(Text, nullable=False)
    start_time   = Column(Float, default=0.0)
    end_time     = Column(Float, default=0.0)
    language     = Column(String, default="en")
    created_at   = Column(DateTime(timezone=True), server_default=func.now())