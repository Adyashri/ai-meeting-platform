from sqlalchemy import Column, String, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base
import uuid

def _uuid():
    return str(uuid.uuid4())

class Meeting(Base):
    __tablename__ = "meetings"

    id         = Column(String, primary_key=True, default=_uuid)
    title      = Column(String(255), nullable=False)
    room_code  = Column(String(20), unique=True, nullable=False)
    host_id    = Column(String, ForeignKey("users.id"), nullable=True)
    status     = Column(String, default="scheduled")
    agenda     = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at   = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())