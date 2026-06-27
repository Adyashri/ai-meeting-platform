import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id              = Column(String,  primary_key=True, default=lambda: str(uuid.uuid4()))
    name            = Column(String,  nullable=False)
    email           = Column(String,  unique=True, nullable=False, index=True)
    hashed_password = Column(String,  nullable=True)   # ← nullable kiya
    is_google_user  = Column(Boolean, default=False)   # ← naya field
    created_at      = Column(DateTime(timezone=True),  server_default=func.now())