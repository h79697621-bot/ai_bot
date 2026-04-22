import hashlib
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import time
import cv2
import numpy as np

from aiogram import Bot
from aiogram.types import InputFile, BufferedInputFile
from aiogram.exceptions import TelegramAPIError

from exceptions import ProcessingError
from .helpers import safe_filename

logger = logging.getLogger(__name__)


class StickerPackManager:
    """Manage Telegram sticker pack creation and updates"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        
    async def generate_pack_name(self, user_id: int, pack_type: str = "emoji") -> str:
        """
        Generate unique sticker pack name
        
        Args:
            user_id: User ID
            pack_type: Type of pack (emoji, grid, video)
            
        Returns:
            Unique pack name for Telegram
        """
        # Get bot username
        try:
            bot_info = await self.bot.get_me()
            bot_username = bot_info.username
        except:
            bot_username = "emojipackbot"  # Fallback
        
        # Create unique identifier
        timestamp = int(time.time())
        hash_input = f"{user_id}_{pack_type}_{timestamp}"
        pack_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        
        # Telegram pack name format: must end with _by_botusername
        pack_name = f"pack_{user_id}_{pack_hash}_by_{bot_username}"
        
        return pack_name
    
    def generate_pack_title(self, user_name: str, grid_size: tuple, pack_type: str = "emoji") -> str:
        """
        Generate human-readable pack title
        
        Args:
            user_name: User's display name
            grid_size: (width, height) of the grid
            pack_type: Type of pack
            
        Returns:
            Pack title for display
        """
        grid_x, grid_y = grid_size
        safe_name = safe_filename(user_name)
        bot_tag = "@media_to_emoji_bot"

        if pack_type == "video":
            return f"{safe_name}'s Animated Emojis ({grid_x}×{grid_y}) {bot_tag}"
        else:
            return f"{safe_name}'s Emoji Pack ({grid_x}×{grid_y}) {bot_tag}"
    
    async def create_sticker_pack(
        self,
        user_id: int,
        user_name: str,
        emoji_files: List[Path],
        grid_size: tuple,
        pack_type: str = "emoji",
        animated: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new Telegram sticker pack
        
        Args:
            user_id: User ID
            user_name: User's display name
            emoji_files: List of emoji file paths
            grid_size: (width, height) of the grid
            pack_type: Type of pack
            animated: Whether to create animated emoji pack
            
        Returns:
            Dict with pack info including link
        """
        try:
            if not emoji_files:
                raise ProcessingError("No emoji files provided")
            
            # Generate pack identifiers
            pack_name = await self.generate_pack_name(user_id, pack_type)
            pack_title = self.generate_pack_title(user_name, grid_size, pack_type)
            
            logger.info(f"Creating sticker pack '{pack_name}' for user {user_id}")
            
            # Prepare stickers list
            stickers = []
            emoji_list = self._generate_emoji_list(len(emoji_files))
            
            for i, file_path in enumerate(emoji_files[:50]):  # Telegram limit: 50 stickers per creation
                if not file_path.exists():
                    logger.warning(f"Emoji file not found: {file_path}")
                    continue
                
                # Determine format and optimize file
                if animated and file_path.suffix.lower() == '.webm':
                    # For animated WebM files
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    input_file = BufferedInputFile(
                        file_content,
                        filename=f"emoji_{i+1}.webm"
                    )
                    
                    sticker_format = "video"
                else:
                    # For static PNG files  
                    file_content = self._optimize_image_for_telegram(file_path)
                    
                    input_file = BufferedInputFile(
                        file_content,
                        filename=f"emoji_{i+1}.png"
                    )
                    
                    sticker_format = "static"
                
                # Add to stickers list
                sticker_data = {
                    "sticker": input_file,
                    "format": sticker_format,
                    "emoji_list": [emoji_list[i % len(emoji_list)]]
                }
                stickers.append(sticker_data)
            
            if not stickers:
                raise ProcessingError("No valid emoji files found")
            
            # Use custom emoji for both static and animated emoji packs
            sticker_type = "custom_emoji"
            
            try:
                success = await self.bot.create_new_sticker_set(
                    user_id=user_id,
                    name=pack_name,
                    title=pack_title,
                    stickers=stickers,
                    sticker_type=sticker_type
                )
            except TelegramAPIError as e:
                logger.error(f"Failed to create custom emoji pack: {e}")
                raise
            
            if success:
                # Use appropriate link based on sticker type
                if sticker_type == "custom_emoji":
                    pack_link = f"https://t.me/addemoji/{pack_name}"
                else:
                    pack_link = f"https://t.me/addstickers/{pack_name}"
                
                result = {
                    "success": True,
                    "pack_name": pack_name,
                    "pack_title": pack_title,
                    "pack_link": pack_link,
                    "sticker_count": len(stickers),
                    "grid_size": grid_size,
                    "pack_type": sticker_type
                }
                
                logger.info(f"Successfully created sticker pack: {pack_link}")
                return result
            else:
                raise ProcessingError("Failed to create sticker pack")
                
        except TelegramAPIError as e:
            logger.error(f"Telegram API error creating sticker pack: {e}")
            
            # Handle specific errors
            if "STICKERSET_INVALID" in str(e):
                error_msg = "Invalid sticker set configuration"
            elif "PEER_ID_INVALID" in str(e):
                error_msg = "Invalid user ID"
            elif "STICKERS_EMPTY" in str(e):
                error_msg = "No valid stickers provided"
            else:
                error_msg = f"Telegram API error: {str(e)}"
            
            return {
                "success": False,
                "error": error_msg,
                "pack_name": None,
                "pack_link": None
            }
            
        except Exception as e:
            logger.error(f"Error creating sticker pack: {e}")
            return {
                "success": False,
                "error": f"Failed to create sticker pack: {str(e)}",
                "pack_name": None,
                "pack_link": None
            }
    
    async def add_stickers_to_pack(
        self,
        user_id: int,
        pack_name: str,
        emoji_files: List[Path]
    ) -> bool:
        """
        Add more stickers to existing pack
        
        Args:
            user_id: User ID (pack owner)
            pack_name: Existing pack name
            emoji_files: Additional emoji files
            
        Returns:
            True if successful
        """
        try:
            emoji_list = self._generate_emoji_list(len(emoji_files))
            
            for i, file_path in enumerate(emoji_files):
                if not file_path.exists():
                    continue
                
                # Optimize file for Telegram
                file_content = self._optimize_image_for_telegram(file_path)
                
                # Create input file
                input_file = BufferedInputFile(
                    file_content,
                    filename=f"emoji_add_{i+1}.png"
                )
                
                # Add sticker to existing set
                success = await self.bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_name,
                    sticker={
                        "sticker": input_file,
                        "format": "static",
                        "emoji_list": [emoji_list[i % len(emoji_list)]]
                    }
                )
                
                if not success:
                    logger.warning(f"Failed to add sticker {i+1} to pack {pack_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding stickers to pack: {e}")
            return False
    
    async def get_pack_info(self, pack_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about existing sticker pack
        
        Args:
            pack_name: Name of the pack
            
        Returns:
            Pack information or None if not found
        """
        try:
            sticker_set = await self.bot.get_sticker_set(pack_name)
            
            return {
                "name": sticker_set.name,
                "title": sticker_set.title,
                "sticker_count": len(sticker_set.stickers),
                "link": f"https://t.me/addemoji/{sticker_set.name}"
            }
            
        except Exception as e:
            logger.warning(f"Could not get pack info for {pack_name}: {e}")
            return None
    
    def _generate_emoji_list(self, count: int) -> List[str]:
        """
        Generate list of emojis for stickers
        
        Args:
            count: Number of emojis needed
            
        Returns:
            List of emoji characters
        """
        # Base emoji set
        base_emojis = [
            "😀", "😃", "😄", "😁", "😅", "😂", "🤣", "😊", "😇", "🙂",
            "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚", "😋",
            "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳",
            "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", "😖",
            "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", "🤯"
        ]
        
        # Extend if needed
        emoji_list = []
        for i in range(count):
            emoji_list.append(base_emojis[i % len(base_emojis)])
        
        return emoji_list
    
    async def delete_sticker_pack(self, pack_name: str) -> bool:
        """
        Delete a sticker pack (if possible)
        
        Args:
            pack_name: Name of pack to delete
            
        Returns:
            True if successful
        """
        try:
            # Note: Telegram doesn't allow bots to delete sticker packs
            # This method is here for completeness but will likely fail
            await self.bot.delete_sticker_set(pack_name)
            return True
            
        except Exception as e:
            logger.warning(f"Could not delete pack {pack_name}: {e}")
            return False
    
    def _optimize_image_for_telegram(self, image_path: Path) -> bytes:
        """
        Optimize image for Telegram sticker requirements
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Optimized image as bytes
        """
        try:
            # Load image
            image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
            if image is None:
                raise ProcessingError(f"Could not load image: {image_path}")
            
            # Ensure image is 100x100 for custom emoji (not 512x512 for stickers)
            if image.shape[:2] != (100, 100):
                image = cv2.resize(image, (100, 100), interpolation=cv2.INTER_LANCZOS4)
            
            # Convert to RGBA if needed (for PNG with transparency)
            if len(image.shape) == 3 and image.shape[2] == 3:
                # BGR to BGRA
                image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
            
            # Try different compression levels to stay under 512KB (much smaller for 100x100 images)
            max_file_size = 256 * 1024  # 256KB to be safe for custom emoji
            
            # Start with high compression
            for compression in [9, 8, 7, 6, 5, 4, 3]:
                encode_params = [cv2.IMWRITE_PNG_COMPRESSION, compression]
                success, buffer = cv2.imencode('.png', image, encode_params)
                
                if success and len(buffer) < max_file_size:
                    logger.debug(f"Optimized image: {len(buffer)} bytes with compression {compression}")
                    return buffer.tobytes()
            
            # If still too large, try reducing image quality
            # Convert to RGB and use JPEG compression
            if len(image.shape) == 4:
                # BGRA to BGR (remove alpha)
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            else:
                image_rgb = image
            
            for quality in [95, 90, 85, 80, 75, 70]:
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
                success, buffer = cv2.imencode('.jpg', image_rgb, encode_params)
                
                if success and len(buffer) < max_file_size:
                    logger.debug(f"Optimized image as JPEG: {len(buffer)} bytes with quality {quality}")
                    return buffer.tobytes()
            
            # Last resort: heavily compress PNG
            encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
            success, buffer = cv2.imencode('.png', image, encode_params)
            
            if success:
                logger.warning(f"Image size: {len(buffer)} bytes (may be too large for Telegram)")
                return buffer.tobytes()
            else:
                raise ProcessingError("Failed to encode image")
                
        except Exception as e:
            logger.error(f"Failed to optimize image {image_path}: {e}")
            # Fallback: read original file
            with open(image_path, 'rb') as f:
                return f.read()
    
    def _resize_webm_for_stickers(self, webm_path: Path) -> bytes:
        """
        Resize WebM from 100x100 (emoji) to 512x512 (stickers) 
        
        Args:
            webm_path: Path to 100x100 WebM file
            
        Returns:
            Resized WebM file content as bytes
        """
        try:
            import subprocess
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.webm') as temp_file:
                temp_path = temp_file.name
                
                # Use ffmpeg to resize WebM from 100x100 to 512x512
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(webm_path),
                    '-vf', 'scale=512:512:flags=lanczos',
                    '-c:v', 'libvpx',  # Use VP8 for compatibility
                    '-b:v', '256k',
                    '-crf', '30', 
                    '-g', '15',
                    '-auto-alt-ref', '0',
                    temp_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    with open(temp_path, 'rb') as f:
                        content = f.read()
                    logger.info(f"Resized WebM to 512x512: {len(content)} bytes")
                    return content
                else:
                    logger.error(f"WebM resize failed: {result.stderr}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to resize WebM for stickers: {e}")
            return None
    
    def generate_pack_link(self, pack_name: str) -> str:
        """
        Generate link to sticker pack
        
        Args:
            pack_name: Name of the pack
            
        Returns:
            Direct link to add stickers
        """
        return f"https://t.me/addemoji/{pack_name}"