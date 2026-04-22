import time
asyncio
from typing import Callable, Dict, Any, Awaitable
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class ThrottlingMiddleware(BaseMiddleware):
    """Middleware for rate limiting user requests"""
    
    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize throttling middleware
        
        Args:
            rate_limit: Maximum requests per second per user
        """
        self.rate_limit = rate_limit
        self.user_last_request = defaultdict(float)
    
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        
        # Calculate time since last request
        last_request_time = self.user_last_request[user_id]
        time_since_last = current_time - last_request_time
        
        # Check if user is rate limited
        min_interval = 1.0 / self.rate_limit
        if time_since_last < min_interval:
            # Calculate how long to wait
            wait_time = min_interval - time_since_last
            
            # For messages, send a throttling warning
            if isinstance(event, Message) and wait_time > 0.5:  # Only warn for significant delays
                try:
                    await event.answer(
                        f"⏱️ Please slow down! Wait {wait_time:.1f} seconds before sending another message.",
                        show_alert=False
                    )
                except:
                    pass  # Ignore if we can't send the message
            
            # Wait for the remaining time
            await asyncio.sleep(wait_time)
        
        # Update last request time
        self.user_last_request[user_id] = time.time()
        
        # Execute handler
        return await handler(event, data)
    
    def cleanup_old_entries(self, max_age: float = 3600):
        """Clean up old user entries (call periodically)"""
        current_time = time.time()
        expired_users = [
            user_id for user_id, last_time in self.user_last_request.items()
            if current_time - last_time > max_age
        ]
        
        for user_id in expired_users:
            del self.user_last_request[user_id]
