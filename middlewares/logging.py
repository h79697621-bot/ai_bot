import logging
import time
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging user interactions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        
        # Log incoming event
        if isinstance(event, Message):
            user_id = event.from_user.id
            user_name = event.from_user.first_name or "Unknown"
            
            if event.text:
                self.logger.info(f"Message from {user_name} ({user_id}): {event.text[:50]}...")
            elif event.photo:
                self.logger.info(f"Photo from {user_name} ({user_id})")
            elif event.video:
                self.logger.info(f"Video from {user_name} ({user_id})")
            elif event.document:
                self.logger.info(f"Document from {user_name} ({user_id}): {event.document.file_name}")
            else:
                self.logger.info(f"Other message from {user_name} ({user_id})")
                
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            user_name = event.from_user.first_name or "Unknown"
            self.logger.info(f"Callback from {user_name} ({user_id}): {event.data}")
        
        try:
            # Execute handler
            result = await handler(event, data)
            
            # Log execution time
            execution_time = time.time() - start_time
            if execution_time > 1.0:  # Log slow operations
                self.logger.warning(f"Slow operation: {execution_time:.2f}s for user {user_id}")
            
            return result
            
        except Exception as e:
            # Log errors
            execution_time = time.time() - start_time
            self.logger.error(f"Handler error after {execution_time:.2f}s for user {user_id}: {e}")
            raise