from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routers import auth

app = FastAPI()

app.include_router(auth.router)

Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "AI Meeting Platform API is running!"}