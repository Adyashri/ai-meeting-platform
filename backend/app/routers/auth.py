from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from starlette.requests import Request

from app.database import SessionLocal
from app.models.user import User
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Pydantic Models ───────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Current User Dependency ───────────────────────────────────
def get_current_user(token: str = Depends(oauth2_scheme)):
    db = SessionLocal()
    try:
        payload  = decode_access_token(token)
        user_id  = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    finally:
        db.close()


# ── Register ──────────────────────────────────────────────────
@router.post("/register")
def register(data: RegisterRequest):
    db = SessionLocal()
    try:
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
            "message": "Registration successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email
            }
        }
    finally:
        db.close()


# ── Login (JSON body — frontend ke liye) ─────────────────────
@router.post("/login")
def login(data: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.email == data.email
        ).first()
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        token = create_access_token(data={"user_id": user.id})
        return {
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email
            }
        }
    finally:
        db.close()


# ── Get Current User ──────────────────────────────────────────
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email
    }


# ── Google OAuth ──────────────────────────────────────────────
# Google OAuth sirf tab kaam karega jab GOOGLE_CLIENT_ID set ho
@router.get("/google/login")
async def google_login(request: Request):
    """
    Google OAuth login.
    Pehle Google Cloud Console mein credentials banao:
    1. console.cloud.google.com pe jao
    2. New Project banao
    3. APIs & Services → Credentials → Create OAuth Client ID
    4. Application type: Web application
    5. Authorized redirect URIs: http://localhost:8000/auth/google/callback
    6. Client ID aur Secret .env mein daalo
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured. Add GOOGLE_CLIENT_ID to .env"
        )

    try:
        from authlib.integrations.starlette_client import OAuth
        oauth = OAuth()
        oauth.register(
            name="google",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_kwargs={"scope": "openid email profile"},
        )
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google OAuth error: {str(e)}")


@router.get("/google/callback")
async def google_callback(request: Request):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured"
        )

    db = SessionLocal()
    try:
        from authlib.integrations.starlette_client import OAuth
        oauth = OAuth()
        oauth.register(
            name="google",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_kwargs={"scope": "openid email profile"},
        )

        token     = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            resp      = await oauth.google.userinfo(token=token)
            user_info = dict(resp) if resp else None

        if not user_info:
            raise HTTPException(
                status_code=400,
                detail="Google login failed — no user info"
            )

        email = user_info.get("email")
        name  = user_info.get("name") or "Google User"

        if not email:
            raise HTTPException(
                status_code=400,
                detail="Google did not provide email"
            )

        # Check if user already exists
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name=name,
                email=email,
                hashed_password=hash_password(email + "_google_oauth")
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"user_id": user.id})

        # Redirect to frontend
        redirect_url = (
            f"{settings.FRONTEND_URL}/login-success"
            f"?token={quote(access_token)}"
            f"&name={quote(user.name)}"
            f"&user_id={quote(str(user.id))}"
            f"&email={quote(user.email)}"
        )
        return RedirectResponse(url=redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        error_url = f"{settings.FRONTEND_URL}/login?error={quote(str(e))}"
        return RedirectResponse(url=error_url)
    finally:
        db.close()