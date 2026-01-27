"""Configuration management via environment variables."""
import os
from typing import Optional


class Config:
    """Application configuration loaded from environment variables."""
    
    DATABASE_URL: str
    WEBHOOK_SECRET: str
    LOG_LEVEL: str
    
    def __init__(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
        self.WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    def validate(self) -> Optional[str]:
        """Validate required configuration. Returns error message if invalid."""
        if not self.WEBHOOK_SECRET:
            return "WEBHOOK_SECRET environment variable is required"
        return None


config = Config()
