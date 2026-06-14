from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class MOM(Base):
    __tablename__ = "moms"

    id = Column(Integer, primary_key=True)
    meeting_id = Column(String, ForeignKey("meetings.id"))
    summary = Column(String)
    action_items = Column(String)