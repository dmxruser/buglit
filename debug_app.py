from fastapi import FastAPI
from config import settings
import os

app = FastAPI()

@app.get("/")
def read_root():
    # This endpoint will only be reached if the settings are loaded successfully
    return {
        "message": "Hello World from Debug App",
        "github_app_id": settings.GITHUB_APP_ID,
        "gemini_api_key_set": "Yes" if settings.GEMINI_API_KEY else "No",
        "frontend_url": settings.FRONTEND_URL,
        "private_key_loaded": "Yes" if settings.private_key_bytes else "No"
    }
