import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


async def run_with_timeout(coro, timeout: int) -> Any:
    """Run coroutine with timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Operation timed out after {timeout} seconds")
        raise


def safe_filename(filename: str, max_length: int = 100) -> str:
    """Create safe filename by removing/replacing problematic characters"""
    import re
    
    # Remove or replace problematic characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = re.sub(r'\s+', '_', safe_name)  # Replace spaces with underscores
    safe_name = safe_name.strip('._')  # Remove leading/trailing dots and underscores
    
    # Limit length
    if len(safe_name) > max_length:
        name_part, ext = Path(safe_name).stem, Path(safe_name).suffix
        safe_name = name_part[:max_length - len(ext)] + ext
    
    return safe_name or "unnamed_file"


def get_file_hash(file_path: Path) -> str:
    """Get MD5 hash of file for caching"""
    import hashlib
    
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def calculate_processing_time_estimate(file_size_mb: float, grid_cells: int) -> int:
    """Estimate processing time in seconds"""
    # Base time per MB and per grid cell (rough estimates)
    base_time_per_mb = 2  # seconds
    time_per_cell = 0.5   # seconds
    
    estimated_time = (file_size_mb * base_time_per_mb) + (grid_cells * time_per_cell)
    return max(int(estimated_time), 5)  # Minimum 5 seconds


class ProgressTracker:
    """Track and report processing progress"""
    
    def __init__(self, total_steps: int, callback: Optional[Callable] = None):
        self.total_steps = total_steps
        self.current_step = 0
        self.callback = callback
        self.start_time = time.time()
    
    def update(self, step_increment: int = 1, message: str = None):
        """Update progress"""
        self.current_step += step_increment
        progress = min(self.current_step / self.total_steps, 1.0)
        
        if self.callback:
            self.callback(progress, message)
        
        if message:
            logger.info(f"Progress: {progress:.1%} - {message}")
    
    def get_eta(self) -> Optional[int]:
        """Get estimated time remaining in seconds"""
        if self.current_step == 0:
            return None
        
        elapsed = time.time() - self.start_time
        remaining_steps = self.total_steps - self.current_step
        time_per_step = elapsed / self.current_step
        
        return int(remaining_steps * time_per_step)