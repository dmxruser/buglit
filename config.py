from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional
import os

class Settings(BaseSettings):
    # GitHub App settings
    GITHUB_APP_ID: str
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_PRIVATE_KEY_PATH: str

    @property
    def private_key_bytes(self) -> bytes:
        with open(self.GITHUB_PRIVATE_KEY_PATH, 'rb') as f:
            return f.read()
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Gemini AI settings
    GEMINI_API_KEY: str
    
    # Application settings
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Cache settings
    CACHE_TTL: int = 300  # 5 minutes
    
    # File paths
    BASE_DIR: Path = Path(__file__).parent
    if os.getenv("VERCEL") == "1":
        TEMP_DIR: Path = Path("/tmp")
    else:
        TEMP_DIR: Path = BASE_DIR / "tmp"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = 'ignore'  # Ignore extra fields in .env file

# Initialize settings
settings = Settings()

# Ensure temp directory exists
settings.TEMP_DIR.mkdir(exist_ok=True)
