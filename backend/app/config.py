from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey123456789")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

settings = Settings()

# get_settings function — whisper_service ke liye zaroori
def get_settings():
    return settings