import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Optional
import aiofiles
import aiofiles.os

from aiogram import Bot
from aiogram.types import File as TelegramFile

from config import CACHE_DIR, IMAGES_CACHE_DIR, VIDEOS_CACHE_DIR
from exceptions import FileFormatError, FileSizeError
from .helpers import safe_filename, get_file_hash
from .validation import validate_file_size, validate_file_format

logger = logging.getLogger(__name__)


class FileManager:
    """Manage file downloads, uploads, and cache cleanup"""
    
    def __init__(self, bot: Bot, max_file_size_mb: int = 50):
        self.bot = bot
        self.max_file_size_mb = max_file_size_mb
    
    async def download_media(self, file_info: TelegramFile, user_id: int) -> Path:
        """Download media file from Telegram"""
        try:
            # Validate file size
            if file_info.file_size and file_info.file_size > self.max_file_size_mb * 1024 * 1024:
                raise FileSizeError(f"File size exceeds {self.max_file_size_mb}MB limit")
            
            # Determine file extension and target directory
            file_path_parts = Path(file_info.file_path).parts
            filename = file_path_parts[-1] if file_path_parts else "unknown"
            safe_name = safe_filename(filename)
            
            # Determine media type and target directory
            try:
                media_type = validate_file_format(Path(file_info.file_path))
                if media_type == "image":
                    target_dir = IMAGES_CACHE_DIR
                else:
                    target_dir = VIDEOS_CACHE_DIR
            except Exception:
                # Fallback to generic cache dir
                target_dir = CACHE_DIR
            
            # Create unique filename with user_id and timestamp
            timestamp = int(time.time())
            unique_filename = f"{user_id}_{timestamp}_{safe_name}"
            local_path = target_dir / unique_filename
            
            # Download file
            await self.bot.download(file_info, destination=local_path)
            
            # Validate downloaded file
            validate_file_size(local_path, self.max_file_size_mb)
            media_type = validate_file_format(local_path)
            
            logger.info(f"Downloaded {media_type} file: {local_path} ({local_path.stat().st_size} bytes)")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download file {file_info.file_path}: {e}")
            
            # Clean up partially downloaded file if it exists
            if 'local_path' in locals() and local_path.exists():
                try:
                    local_path.unlink()
                    logger.debug(f"Cleaned up partially downloaded file: {local_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup partially downloaded file: {cleanup_error}")
            
            raise
    
    async def cleanup_user_files(self, user_id: int, max_age_hours: int = 1):
        """Clean up old files for a specific user"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        cleaned_count = 0
        for cache_dir in [IMAGES_CACHE_DIR, VIDEOS_CACHE_DIR, CACHE_DIR]:
            if not cache_dir.exists():
                continue
                
            async for file_path in self._async_glob(cache_dir, f"{user_id}_*"):
                try:
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        await aiofiles.os.remove(file_path)
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up file {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old files for user {user_id}")
        
        return cleaned_count
    
    async def cleanup_cache(self, max_age_hours: int = 1):
        """Clean up all old cache files"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        total_cleaned = 0
        total_size_freed = 0
        
        for cache_dir in [IMAGES_CACHE_DIR, VIDEOS_CACHE_DIR, CACHE_DIR]:
            if not cache_dir.exists():
                continue
            
            async for file_path in self._async_glob(cache_dir, "*"):
                try:
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_size = file_path.stat().st_size
                        await aiofiles.os.remove(file_path)
                        total_cleaned += 1
                        total_size_freed += file_size
                        logger.debug(f"Cleaned up old file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up file {file_path}: {e}")
        
        if total_cleaned > 0:
            size_mb = total_size_freed / (1024 * 1024)
            logger.info(f"Cache cleanup: removed {total_cleaned} files, freed {size_mb:.1f}MB")
        
        return total_cleaned, total_size_freed
    
    async def get_cache_stats(self) -> Dict[str, int]:
        """Get cache directory statistics"""
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "image_files": 0,
            "video_files": 0,
        }
        
        for cache_dir, file_type in [(IMAGES_CACHE_DIR, "image"), (VIDEOS_CACHE_DIR, "video")]:
            if not cache_dir.exists():
                continue
            
            dir_files = 0
            dir_size = 0
            
            async for file_path in self._async_glob(cache_dir, "*"):
                if file_path.is_file():
                    dir_files += 1
                    dir_size += file_path.stat().st_size
            
            stats["total_files"] += dir_files
            stats["total_size_mb"] += dir_size / (1024 * 1024)
            stats[f"{file_type}_files"] = dir_files
        
        return stats
    
    async def _async_glob(self, directory: Path, pattern: str):
        """Async generator for globbing files"""
        try:
            for file_path in directory.glob(pattern):
                yield file_path
                await asyncio.sleep(0)  # Yield control
        except Exception as e:
            logger.error(f"Error globbing {directory}/{pattern}: {e}")
    
    def get_output_path(self, user_id: int, base_name: str, extension: str = ".png") -> Path:
        """Generate output file path for processed emoji"""
        timestamp = int(time.time())
        safe_name = safe_filename(base_name)
        filename = f"{user_id}_{timestamp}_{safe_name}{extension}"
        return CACHE_DIR / filename