import os
from pathlib import Path
from typing import Tuple

from exceptions import ValidationError, GridSizeError, FileTypeError, ParameterError


SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
SUPPORTED_VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".webm", ".mkv"}


def validate_grid_size(grid_x: int, grid_y: int, min_size: int = 1, max_size: int = 20) -> bool:
    """Validate grid dimensions"""
    if not isinstance(grid_x, int) or not isinstance(grid_y, int):
        raise GridSizeError("Grid dimensions must be integers")
    
    if grid_x < min_size or grid_y < min_size:
        raise GridSizeError(f"Grid dimensions must be at least {min_size}x{min_size}")
    
    if grid_x > max_size or grid_y > max_size:
        raise GridSizeError(f"Grid dimensions cannot exceed {max_size}x{max_size}")
    
    return True


def validate_adaptation_method(method: str) -> bool:
    """Validate image adaptation method"""
    valid_methods = {"pad", "stretch", "crop"}
    if method not in valid_methods:
        raise ParameterError(f"Invalid adaptation method. Must be one of: {valid_methods}")
    return True


def validate_file_format(file_path: Path, media_type: str = None) -> str:
    """Validate file format and return media type"""
    if not file_path.exists():
        raise FileTypeError(f"File does not exist: {file_path}")
    
    suffix = file_path.suffix.lower()
    
    if suffix in SUPPORTED_IMAGE_FORMATS:
        detected_type = "image"
    elif suffix in SUPPORTED_VIDEO_FORMATS:
        detected_type = "video"
    else:
        raise FileTypeError(f"Unsupported file format: {suffix}")
    
    if media_type and media_type != detected_type:
        raise FileTypeError(f"Expected {media_type} but got {detected_type}")
    
    return detected_type


def validate_file_size(file_path: Path, max_size_mb: int = 50) -> bool:
    """Validate file size"""
    if not file_path.exists():
        raise FileTypeError(f"File does not exist: {file_path}")
    
    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise FileTypeError(f"File size ({size_mb:.1f}MB) exceeds limit ({max_size_mb}MB)")
    
    return True


def validate_grid_and_method(grid_x: int, grid_y: int, method: str) -> Tuple[int, int, str]:
    """Validate grid size and adaptation method together"""
    validate_grid_size(grid_x, grid_y)
    validate_adaptation_method(method)
    return grid_x, grid_y, method