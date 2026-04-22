import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BotConfig:
    telegram_bot_token: str
    admin_user_id: int = 0
    max_grid_size: int = 8
    min_grid_size: int = 2
    max_file_size_mb: int = 50
    max_video_duration: int = 300
    processing_timeout: int = 120
    cache_cleanup_interval: int = 3600
    log_level: str = "INFO"
    redis_url: Optional[str] = None
    database_url: Optional[str] = None


def load_config() -> BotConfig:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # dotenv is optional, continue without it
        pass
    
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    
    return BotConfig(
        telegram_bot_token=telegram_bot_token,
        admin_user_id=int(os.getenv("ADMIN_USER_ID", "0")),
        max_grid_size=int(os.getenv("MAX_GRID_SIZE", "8")),
        min_grid_size=int(os.getenv("MIN_GRID_SIZE", "2")),
        max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
        max_video_duration=int(os.getenv("MAX_VIDEO_DURATION", "300")),
        processing_timeout=int(os.getenv("PROCESSING_TIMEOUT", "120")),
        cache_cleanup_interval=int(os.getenv("CACHE_CLEANUP_INTERVAL", "3600")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        redis_url=os.getenv("REDIS_URL"),
        database_url=os.getenv("DATABASE_URL"),
    )


PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
IMAGES_CACHE_DIR = CACHE_DIR / "images"
VIDEOS_CACHE_DIR = CACHE_DIR / "videos"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_CACHE_DIR.mkdir(parents=True, exist_ok=True)