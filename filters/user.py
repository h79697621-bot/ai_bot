from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Union, List, Optional


class IsPrivateChatFilter(BaseFilter):
    """Filter for private chat messages"""
    
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        if isinstance(obj, CallbackQuery):
            message = obj.message
        else:
            message = obj
        
        return message.chat.type == "private"


class IsAdminFilter(BaseFilter):
    """Filter for admin users"""
    
    def __init__(self, admin_ids: Optional[List[int]] = None):
        self.admin_ids = admin_ids or []
    
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        if not self.admin_ids:
            return False
        
        if isinstance(obj, CallbackQuery):
            user_id = obj.from_user.id
        else:
            user_id = obj.from_user.id
        
        return user_id in self.admin_ids


class RateLimitFilter(BaseFilter):
    """Filter for rate limiting (basic implementation)"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_requests = {}
    
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        import time
        
        if isinstance(obj, CallbackQuery):
            user_id = obj.from_user.id
        else:
            user_id = obj.from_user.id
        
        current_time = time.time()
        
        # Clean old requests
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if current_time - req_time < self.window_seconds
            ]
        else:
            self.user_requests[user_id] = []
        
        # Check if user has exceeded rate limit
        if len(self.user_requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.user_requests[user_id].append(current_time)
        return True


class HasUserSettingsFilter(BaseFilter):
    """Filter for users with existing settings"""
    
    def __init__(self, user_settings_store: dict):
        self.user_settings_store = user_settings_store
    
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        if isinstance(obj, CallbackQuery):
            user_id = obj.from_user.id
        else:
            user_id = obj.from_user.id
        
        return user_id in self.user_settings_store


class TextContainsFilter(BaseFilter):
    """Filter for messages containing specific text"""
    
    def __init__(self, texts: List[str], case_sensitive: bool = False):
        self.texts = texts if case_sensitive else [t.lower() for t in texts]
        self.case_sensitive = case_sensitive
    
    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        
        text = message.text if self.case_sensitive else message.text.lower()
        return any(search_text in text for search_text in self.texts)
