from fastapi import APIRouter
from app.schemas.auth import RegisterRequest
from app.services.auth_service import hash_password
from app.models import User
from app.database import SessionLocal

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
def register(data: RegisterRequest):

    db = SessionLocal()

    hashed_pw = hash_password(data.password)

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hashed_pw
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": user.id
    }