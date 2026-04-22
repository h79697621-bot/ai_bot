#!/usr/bin/env python3
"""
Telegram Emoji Pack Bot - Main Entry Point

A Telegram bot that converts user-uploaded images and videos into custom emoji packs
with configurable grid dimensions using Python, OpenCV, and NumPy.
"""

import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession

from config import load_config
from handlers import setup_user_handlers
from middlewares.logging import LoggingMiddleware
from middlewares.throttling import ThrottlingMiddleware


async def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )
    
    # Set specific log levels
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def setup_bot_and_dispatcher():
    """Setup bot and dispatcher with all components"""
    try:
        # Load configuration
        config = load_config()
        
        # Create bot session with timeout settings
        session = AiohttpSession()
        
        # Initialize bot and dispatcher
        bot = Bot(
            token=config.telegram_bot_token,
            session=session
        )
        
        # Use memory storage for FSM (in production, consider Redis)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Setup middlewares
        dp.message.middleware(LoggingMiddleware())
        dp.callback_query.middleware(LoggingMiddleware())
        dp.message.middleware(ThrottlingMiddleware(rate_limit=3))  # 3 messages per second
        dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=5))  # 5 callbacks per second
        
        # Setup handlers
        setup_user_handlers(dp)
        
        logging.info("Bot and dispatcher setup completed")
        return bot, dp, config
        
    except Exception as e:
        logging.error(f"Failed to setup bot: {e}")
        raise


async def on_startup():
    """Execute on bot startup"""
    logging.info("🚀 Telegram Emoji Pack Bot is starting...")
    
    # Ensure cache directories exist
    from config import CACHE_DIR, IMAGES_CACHE_DIR, VIDEOS_CACHE_DIR
    for cache_dir in [CACHE_DIR, IMAGES_CACHE_DIR, VIDEOS_CACHE_DIR]:
        cache_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Cache directory ready: {cache_dir}")
    
    logging.info("✅ Bot startup completed")


async def on_shutdown(bot: Bot):
    """Execute on bot shutdown"""
    logging.info("🛑 Telegram Emoji Pack Bot is shutting down...")
    
    try:
        # Close bot session
        await bot.session.close()
        
        # Cleanup cache files older than 1 hour
        from utils import FileManager
        config = load_config()
        file_manager = FileManager(bot, config.max_file_size_mb)
        cleaned_count, freed_size = await file_manager.cleanup_cache(max_age_hours=1)
        if cleaned_count > 0:
            logging.info(f"Cleaned up {cleaned_count} cache files ({freed_size/(1024*1024):.1f}MB)")
        
    except Exception as e:
        logging.error(f"Error during shutdown: {e}")
    
    logging.info("✅ Bot shutdown completed")


async def periodic_cleanup(bot: Bot, interval_hours: int = 1):
    """Periodic cache cleanup task"""
    from utils import FileManager
    
    config = load_config()
    file_manager = FileManager(bot, config.max_file_size_mb)
    
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)  # Convert hours to seconds
            
            cleaned_count, freed_size = await file_manager.cleanup_cache(max_age_hours=1)
            if cleaned_count > 0:
                logging.info(f"Periodic cleanup: {cleaned_count} files, {freed_size/(1024*1024):.1f}MB freed")
                
        except Exception as e:
            logging.error(f"Periodic cleanup error: {e}")


async def main():
    """Main bot function"""
    try:
        # Setup logging
        await setup_logging()
        
        # Setup bot components
        bot, dp, config = await setup_bot_and_dispatcher()
        
        # Startup procedures
        await on_startup()
        
        # Start periodic cleanup task
        cleanup_task = asyncio.create_task(
            periodic_cleanup(bot, interval_hours=config.cache_cleanup_interval // 3600)
        )
        
        try:
            # Start bot polling
            logging.info("🔄 Starting bot polling...")
            await dp.start_polling(
                bot,
                allowed_updates=["message", "callback_query"],
                skip_updates=True  # Skip pending updates on startup
            )
            
        except KeyboardInterrupt:
            logging.info("👋 Received shutdown signal")
            
        finally:
            # Cancel cleanup task
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            
            # Shutdown procedures
            await on_shutdown(bot)
    
    except Exception as e:
        logging.error(f"Critical error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        # Check Python version
        if sys.version_info < (3, 11):
            print("❌ Python 3.11+ is required")
            sys.exit(1)
        
        # Run the bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)