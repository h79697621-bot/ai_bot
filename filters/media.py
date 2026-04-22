from aiogram.filters import BaseFilter
from aiogram.types import Message
from typing import Union


class IsImageFilter(BaseFilter):
    """Filter for image messages"""
    
    async def __call__(self, message: Message) -> bool:
        if not message.document and not message.photo:
            return False
        
        if message.photo:
            return True
        
        if message.document:
            mime_type = message.document.mime_type or ""
            return mime_type.startswith("image/")
        
        return False


class IsVideoFilter(BaseFilter):
    """Filter for video messages"""
    
    async def __call__(self, message: Message) -> bool:
        if not message.document and not message.video:
            return False
        
        if message.video:
            return True
        
        if message.document:
            mime_type = message.document.mime_type or ""
            return mime_type.startswith("video/")
        
        return False


class IsMediaFilter(BaseFilter):
    """Filter for media messages (image or video)"""
    
    async def __call__(self, message: Message) -> bool:
        image_filter = IsImageFilter()
        video_filter = IsVideoFilter()
        
        return await image_filter(message) or await video_filter(message)


class FileSizeFilter(BaseFilter):
    """Filter for file size limits"""
    
    def __init__(self, max_size_mb: int = 50):
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    async def __call__(self, message: Message) -> bool:
        file_size = None
        
        if message.photo:
            # Get largest photo size
            largest_photo = max(message.photo, key=lambda p: p.file_size or 0)
            file_size = largest_photo.file_size
        elif message.video:
            file_size = message.video.file_size
        elif message.document:
            file_size = message.document.file_size
        
        return file_size is not None and file_size <= self.max_size_bytes


class SupportedFormatFilter(BaseFilter):
    """Filter for supported file formats"""
    
    SUPPORTED_IMAGE_TYPES = {
        "image/jpeg", "image/jpg", "image/png", "image/webp", 
        "image/bmp", "image/tiff", "image/gif"
    }
    
    SUPPORTED_VIDEO_TYPES = {
        "video/mp4", "video/avi", "video/mov", "video/webm", 
        "video/mkv", "video/quicktime"
    }
    
    async def __call__(self, message: Message) -> bool:
        if message.photo:
            return True  # Photos are always supported
        
        mime_type = None
        if message.video:
            mime_type = message.video.mime_type
        elif message.document:
            mime_type = message.document.mime_type
        
        if not mime_type:
            return False
        
        return (mime_type in self.SUPPORTED_IMAGE_TYPES or 
                mime_type in self.SUPPORTED_VIDEO_TYPES)