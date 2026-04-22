import asyncio
import logging
import shutil
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from filters import IsImageFilter, FileSizeFilter, SupportedFormatFilter
from keyboards import get_settings_keyboard, get_processing_complete_keyboard
from states import UserStates
from utils import (
    ImageProcessor, EmojiGenerator, FileManager, ProgressTracker, StickerPackManager,
    validate_file_format, validate_file_size
)
from exceptions import ImageProcessingError, FileSizeError, FileFormatError
from config import load_config, CACHE_DIR
from database import db
from .start import user_settings

logger = logging.getLogger(__name__)
router = Router()

# Initialize processors
image_processor = ImageProcessor()
emoji_generator = EmojiGenerator()


def get_settings_text_for_confirmation(user_id: int) -> str:
    """Generate settings text for image confirmation"""
    settings = user_settings.get(user_id)
    if not settings:
        return "No settings configured."

    method_names = {"pad": "Pad (Keep All)", "stretch": "Stretch", "crop": "Crop"}
    return f"""
🖼️ <b>Image Received!</b>

<b>Current Settings:</b>
• Grid Size: {settings.grid_x}×{settings.grid_y}
• Adaptation: {method_names.get(settings.adaptation_method, settings.adaptation_method)}

<b>Total emojis:</b> {settings.grid_x * settings.grid_y}

Adjust settings if needed, then click "Done" to start processing.
"""


@router.message(
    IsImageFilter(),
    FileSizeFilter(max_size_mb=50),
    SupportedFormatFilter()
)
async def handle_image_upload(message: Message, state: FSMContext, bot: Bot):
    """Handle image upload for processing"""
    user_id = message.from_user.id

    # Track user activity
    db.upsert_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    db.log_activity(user_id, "image_upload")

    # Initialize user settings if not exists
    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    # Store image info in state
    await state.update_data(
        file_id=message.photo[-1].file_id if message.photo else message.document.file_id,
        message_id=message.message_id,
        media_type="image"
    )
    await state.set_state(UserStates.confirming_processing)

    await message.answer(
        get_settings_text_for_confirmation(user_id),
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "start_processing", UserStates.confirming_processing)
async def start_image_processing(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Start image processing"""
    user_id = callback.from_user.id

    # Ensure user has settings
    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    settings = user_settings[user_id]
    data = await state.get_data()

    # Check if this is video processing
    if data.get("media_type") == "video":
        # Let video handler handle this
        return

    try:
        await state.set_state(UserStates.processing_media)

        # Update message to show processing started
        await callback.message.edit_text(
            "🔄 <b>Processing your image...</b>\n\nThis may take a few moments.",
            parse_mode="HTML"
        )
        await callback.answer()

        # Initialize file manager
        config = load_config()
        file_manager = FileManager(bot, config.max_file_size_mb)

        # Get file info and download
        file_info = await bot.get_file(data['file_id'])
        local_path = await file_manager.download_media(file_info, user_id)

        # Validate file
        validate_file_size(local_path, config.max_file_size_mb)
        media_type = validate_file_format(local_path)

        if media_type != "image":
            raise FileFormatError("Expected image file")

        # Progress tracking
        total_steps = 4 + (settings.grid_x * settings.grid_y)
        progress_tracker = ProgressTracker(total_steps)

        # Load and process image
        progress_tracker.update(1, "Loading image...")
        image = image_processor.load_image(local_path)

        # Enhance image if needed
        progress_tracker.update(1, "Processing image...")
        image = image_processor.enhance_image(image, "high")

        # Adapt image to grid ratio
        progress_tracker.update(1, "Adapting image to grid...")
        adapted_image = image_processor.adapt_image_to_grid(
            image, settings.grid_x, settings.grid_y, settings.adaptation_method
        )

        # Split into grid cells
        progress_tracker.update(1, "Splitting into emoji cells...")
        emoji_cells = image_processor.split_image_grid(
            adapted_image, settings.grid_x, settings.grid_y, progress_tracker
        )

        # Apply background removal if enabled
        if settings.background_mode != "keep":
            progress_tracker.update(1, "Processing background...")
            bg_method_map = {
                "remove_white": "white",
                "remove_black": "black",
                "remove_smart": "smart"
            }
            bg_method = bg_method_map.get(settings.background_mode, "smart")
            for i, cell in enumerate(emoji_cells):
                emoji_cells[i] = emoji_generator.add_transparency(cell, method=bg_method)

        # Generate emoji pack
        pack_name = f"emoji_pack_{user_id}"
        output_dir = CACHE_DIR / f"user_{user_id}_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_files = emoji_generator.create_emoji_pack(
            emoji_cells, pack_name, user_id, output_dir, progress_tracker
        )

        # Create ZIP archive
        zip_path = output_dir / f"{pack_name}.zip"
        emoji_generator.create_pack_archive(saved_files, pack_name, zip_path)

        # Create Telegram sticker pack
        sticker_manager = StickerPackManager(bot)
        user_name = callback.from_user.first_name or "User"

        pack_result = await sticker_manager.create_sticker_pack(
            user_id=user_id,
            user_name=user_name,
            emoji_files=saved_files,
            grid_size=(settings.grid_x, settings.grid_y),
            pack_type="emoji"
        )

        # Success message with sticker pack link
        if pack_result["success"]:
            safe_title = pack_result["pack_title"].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            safe_link = pack_result["pack_link"]

            success_text = f"""
✅ <b>Processing Complete!</b>

<b>Results:</b>
• Created: {len(saved_files)} emojis
• Grid: {settings.grid_x}×{settings.grid_y}

🎉 <b>Your Telegram custom emoji pack is ready!</b>

<b>Pack:</b> {safe_title}
<b>Link:</b> <a href="{safe_link}">{safe_link}</a>

Click the link above to add your custom emoji pack to Telegram!

<i>Note: Custom emojis require Telegram Premium to add.</i>
"""
        else:
            error_msg = pack_result.get("error", "Unknown error").replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            success_text = f"""
✅ <b>Processing Complete!</b>

<b>Results:</b>
• Created: {len(saved_files)} emojis
• Grid: {settings.grid_x}×{settings.grid_y}

⚠️ <b>Custom emoji pack creation failed:</b> {error_msg}

You can still download the ZIP file with your emojis below.
"""

        # Store results in state
        await state.update_data(
            emoji_files=[str(f) for f in saved_files],
            zip_path=str(zip_path),
            pack_name=pack_name,
            sticker_pack_result=pack_result
        )

        await callback.message.edit_text(
            success_text,
            reply_markup=get_processing_complete_keyboard(has_sticker_pack=pack_result["success"]),
            parse_mode="HTML"
        )

        # Send first few emojis as preview
        # Preview disabled by default - uncomment to enable
        # await send_emoji_preview(callback.message, saved_files[:4])

        # Clean up original file
        try:
            local_path.unlink()
        except:
            pass

        # Log stickers created to database
        db.log_activity(user_id, "stickers_created", len(saved_files))

        logger.info(f"Successfully processed image for user {user_id}: {len(saved_files)} emojis")

    except Exception as e:
        logger.error(f"Image processing failed for user {user_id}: {e}")

        # Clean up any partially created files
        try:
            if 'local_path' in locals() and local_path and local_path.exists():
                local_path.unlink()

            output_dir = CACHE_DIR / f"user_{user_id}_output"
            if output_dir.exists():
                shutil.rmtree(output_dir)

        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup files after processing error: {cleanup_error}")

        error_text = f"""
❌ <b>Processing Failed</b>

Error: {str(e)[:100]}

Please try again with a different image or settings.
"""

        await callback.message.edit_text(
            error_text,
            parse_mode="HTML"
        )
        await state.clear()


async def send_emoji_preview(message: Message, emoji_files: list, max_preview: int = 4):
    """Send preview of generated emojis"""
    try:
        preview_files = emoji_files[:max_preview]

        if not preview_files:
            return

        await message.answer(f"📱 <b>Preview</b> (showing {len(preview_files)}/{len(emoji_files)} emojis):", parse_mode="HTML")

        for i, emoji_path in enumerate(preview_files):
            if Path(emoji_path).exists():
                try:
                    from aiogram.types import FSInputFile
                    await message.answer_photo(
                        FSInputFile(emoji_path),
                        caption=f"Emoji {i+1}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to send emoji preview {i+1}: {e}")

    except Exception as e:
        logger.warning(f"Failed to send emoji preview: {e}")


@router.callback_query(F.data == "download_zip")
async def download_zip_file(callback: CallbackQuery, state: FSMContext):
    """Send ZIP file to user"""
    data = await state.get_data()
    zip_path = data.get('zip_path')

    if not zip_path or not Path(zip_path).exists():
        await callback.answer("❌ ZIP file not found", show_alert=True)
        return

    try:
        from aiogram.types import FSInputFile
        await callback.message.answer_document(
            FSInputFile(zip_path),
            caption="📦 <b>Your Emoji Pack</b>\n\nExtract and use these PNG files as Telegram stickers!",
            parse_mode="HTML"
        )
        await callback.answer("📦 ZIP file sent!")

    except Exception as e:
        logger.error(f"Failed to send ZIP file: {e}")
        await callback.answer("❌ Failed to send ZIP file", show_alert=True)


@router.callback_query(F.data == "send_stickers")
async def send_individual_stickers(callback: CallbackQuery, state: FSMContext):
    """Send individual emoji files"""
    data = await state.get_data()
    emoji_files = data.get('emoji_files', [])

    if not emoji_files:
        await callback.answer("❌ No emoji files found", show_alert=True)
        return

    await callback.answer("📱 Sending individual emojis...")

    try:
        for i, emoji_path in enumerate(emoji_files):
            if Path(emoji_path).exists():
                from aiogram.types import FSInputFile
                await callback.message.answer_document(
                    FSInputFile(emoji_path),
                    caption=f"Emoji {i+1}/{len(emoji_files)}"
                )
                await asyncio.sleep(0.5)

        await callback.message.answer("✅ All emojis sent individually!")

    except Exception as e:
        logger.error(f"Failed to send individual stickers: {e}")
        await callback.message.answer("❌ Some emojis failed to send")


@router.callback_query(F.data == "process_another")
async def process_another_image(callback: CallbackQuery, state: FSMContext):
    """Process another image - sends new message to preserve sticker pack link"""
    logger.info(f"process_another called by user {callback.from_user.id}")
    await state.clear()

    # Send a new message instead of editing, so user can return to the sticker pack link
    await callback.message.answer(
        "🖼️ <b>Ready for another image!</b>\n\nSend me your next image or video to process.",
        parse_mode="HTML"
    )

    await callback.answer("Ready for next image!")


@router.callback_query(F.data == "add_sticker_pack")
async def add_sticker_pack_to_telegram(callback: CallbackQuery, state: FSMContext):
    """Provide sticker pack link for adding to Telegram"""
    data = await state.get_data()
    pack_result = data.get('sticker_pack_result')

    if not pack_result or not pack_result.get("success"):
        await callback.answer("❌ Sticker pack not available", show_alert=True)
        return

    pack_link = pack_result["pack_link"]
    pack_title = pack_result["pack_title"]

    safe_title = pack_title.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')

    message_text = f"""
🎯 <b>Add Your Custom Emoji Pack to Telegram</b>

<b>Pack Name:</b> {safe_title}

<b>How to add:</b>
1. Click the link below
2. Press "Add Emoji Pack" in Telegram
3. Start using your custom emojis!

<b>Note:</b> You need Telegram Premium to add custom emoji packs.

<b>Link:</b> <a href="{pack_link}">{pack_link}</a>
"""

    keyboard = [
        [
            InlineKeyboardButton(
                text="🎯 Add Emoji Pack to Telegram",
                url=pack_link
            )
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="back_to_results")
        ]
    ]

    await callback.message.edit_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer("🎯 Custom emoji pack link ready!")


@router.callback_query(F.data == "back_to_results")
async def back_to_results(callback: CallbackQuery, state: FSMContext):
    """Go back to processing results"""
    data = await state.get_data()
    pack_result = data.get('sticker_pack_result', {})

    if pack_result.get("success"):
        safe_title = pack_result["pack_title"].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        safe_link = pack_result["pack_link"]
        message_text = f"""
✅ <b>Processing Complete!</b>

🎉 <b>Your Telegram custom emoji pack is ready!</b>

<b>Pack:</b> {safe_title}
<b>Link:</b> <a href="{safe_link}">{safe_link}</a>

Click the link above to add your custom emoji pack to Telegram!
"""
    else:
        message_text = "✅ <b>Processing Complete!</b>\n\nYour emojis are ready for download."

    await callback.message.edit_text(
        message_text,
        reply_markup=get_processing_complete_keyboard(has_sticker_pack=pack_result.get("success", False)),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "delete_files")
async def delete_processing_files(callback: CallbackQuery, state: FSMContext):
    """Delete generated files"""
    data = await state.get_data()

    try:
        # Delete emoji files
        emoji_files = data.get('emoji_files', [])
        for file_path in emoji_files:
            try:
                Path(file_path).unlink()
            except:
                pass

        # Delete ZIP file
        zip_path = data.get('zip_path')
        if zip_path:
            try:
                Path(zip_path).unlink()
            except:
                pass

        await callback.message.edit_text(
            "🗑️ <b>Files deleted successfully!</b>\n\nSend me another image when you're ready.",
            parse_mode="HTML"
        )
        await callback.answer("Files deleted!")
        await state.clear()

    except Exception as e:
        logger.error(f"Failed to delete files: {e}")
        await callback.answer("❌ Some files could not be deleted", show_alert=True)
