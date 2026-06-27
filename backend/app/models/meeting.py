import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    agenda = Column(Text, nullable=True)
    room_code = Column(String, unique=True, nullable=False, index=True)
    host_id = Column(String, ForeignKey("users.id"), nullable=False)

    status = Column(String, default="scheduled")  # scheduled / active / ended
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())