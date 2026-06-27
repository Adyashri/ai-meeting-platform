import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class MOM(Base):
    __tablename__ = "moms"

    id              = Column(String, primary_key=True,
                             default=lambda: str(uuid.uuid4()))
    meeting_id      = Column(String, nullable=False, index=True)
    summary         = Column(Text,   nullable=True)
    # JSON strings — list ko json.dumps se store karo
    key_discussions = Column(Text,   nullable=True, default="[]")
    decisions       = Column(Text,   nullable=True, default="[]")
    action_items    = Column(Text,   nullable=True, default="[]")
    next_meeting    = Column(String, nullable=True)
    created_at      = Column(DateTime(timezone=True),
                             server_default=func.now())
    updated_at      = Column(DateTime(timezone=True),
                             onupdate=func.now())