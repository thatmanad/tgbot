"""
Configuration settings for the Goated Wager Tracker Bot.
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    """Bot configuration settings."""

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str

    # Goated.com API Configuration
    GOATED_API_URL: str

    # Database Configuration
    DATABASE_URL: str

    # Optional configurations with defaults
    GOATED_API_KEY: Optional[str] = None
    BOT_NAME: str = "GoatedWagerBot"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "bot.log"
    MAX_REQUESTS_PER_MINUTE: int = 30
    CACHE_TIMEOUT: int = 300  # 5 minutes

def get_settings() -> Settings:
    """Get bot settings from environment variables."""
    return Settings(
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        GOATED_API_URL=os.getenv("GOATED_API_URL", "https://apis.goated.com"),
        GOATED_API_KEY=os.getenv("GOATED_API_KEY"),
        DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///goated_bot.db"),
        BOT_NAME=os.getenv("BOT_NAME", "GoatedWagerBot"),
        DEBUG=os.getenv("DEBUG", "False").lower() == "true",
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        LOG_FILE=os.getenv("LOG_FILE", "bot.log"),
        MAX_REQUESTS_PER_MINUTE=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "30")),
        CACHE_TIMEOUT=int(os.getenv("CACHE_TIMEOUT", "300"))
    )
