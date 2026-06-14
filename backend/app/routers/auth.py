from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.schemas.auth import RegisterRequest, LoginRequest
from app.services.auth_service import (
    hash_password, verify_password,
    create_access_token, decode_access_token
)
from app.models.user import User
from app.database import SessionLocal

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    db = SessionLocal()
    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    finally:
        db.close()

@router.post("/register")
def register(data: RegisterRequest):
    db = SessionLocal()
    try:
        # Check karo email already exist toh nahi karta
        existing = db.query(User).filter(
            User.email == data.email
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(data={"user_id": user.id})

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }
    finally:
        db.close()

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):

    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == form_data.username
        ).first()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if not verify_password(
            form_data.password,
            user.hashed_password
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        token = create_access_token(
            data={"user_id": user.id}
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }

    finally:
        db.close()

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email
    }