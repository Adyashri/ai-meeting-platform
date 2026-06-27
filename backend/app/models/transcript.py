import uuid
from sqlalchemy import Column, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(String, ForeignKey("meetings.id"), nullable=False, index=True)
    speaker_name = Column(String, nullable=True, default="Unknown")
    text = Column(Text, nullable=False)

    start_time = Column(Float, nullable=True, default=0)
    end_time = Column(Float, nullable=True, default=0)
    language = Column(String, nullable=True, default="en")

    created_at = Column(DateTime(timezone=True), server_default=func.now())