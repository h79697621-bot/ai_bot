import asyncio
import logging
import shutil
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from filters import IsVideoFilter, FileSizeFilter, SupportedFormatFilter
from keyboards import get_settings_keyboard, get_processing_complete_keyboard, get_animation_options_keyboard
from states import UserStates
from utils import (
    VideoProcessor, ImageProcessor, EmojiGenerator, FileManager, ProgressTracker, StickerPackManager,
    validate_file_format, validate_file_size
)
from exceptions import VideoProcessingError, FileSizeError, FileFormatError
from config import load_config, CACHE_DIR
from database import db
from .start import user_settings

logger = logging.getLogger(__name__)
router = Router()

# Initialize processors
video_processor = VideoProcessor()
image_processor = ImageProcessor()
emoji_generator = EmojiGenerator()


def get_video_settings_text(user_id: int, file_size_mb: float = 0, duration: int = 0) -> str:
    """Generate settings text for video confirmation"""
    settings = user_settings.get(user_id)
    if not settings:
        return "No settings configured."

    estimated_frames = min(20, max(5, int(duration / 2))) if duration > 0 else 10
    total_emojis = estimated_frames * (settings.grid_x * settings.grid_y)
    method_names = {"pad": "Pad (Keep All)", "stretch": "Stretch", "crop": "Crop"}

    text = f"""
🎥 <b>Video Received!</b>
⚠️ <i>Video processing is in BETA mode</i>

<b>Video Info:</b>
• Size: {file_size_mb:.1f} MB
• Duration: {duration}s
• Estimated frames: ~{estimated_frames}

<b>Current Settings:</b>
• Grid Size: {settings.grid_x}×{settings.grid_y}
• Adaptation: {method_names.get(settings.adaptation_method, settings.adaptation_method)}

<b>Estimated Output:</b> ~{total_emojis} emojis

Adjust settings if needed, then click "Done" to start processing.
"""
    return text


@router.message(
    IsVideoFilter(),
    FileSizeFilter(max_size_mb=50),
    SupportedFormatFilter()
)
async def handle_video_upload(message: Message, state: FSMContext, bot: Bot):
    """Handle video upload for processing"""
    user_id = message.from_user.id

    # Track user activity
    db.upsert_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    db.log_activity(user_id, "video_upload")

    # Initialize user settings if not exists
    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    settings = user_settings[user_id]

    # Get video info for display
    file_size_mb = 0
    duration = 0

    if message.video:
        file_size_mb = (message.video.file_size or 0) / (1024 * 1024)
        duration = message.video.duration or 0
    elif message.document:
        file_size_mb = (message.document.file_size or 0) / (1024 * 1024)

    # Calculate estimated emoji count
    estimated_frames = min(20, max(5, int(duration / 2))) if duration > 0 else 10

    # Store video info in state
    await state.update_data(
        file_id=message.video.file_id if message.video else message.document.file_id,
        message_id=message.message_id,
        estimated_frames=estimated_frames,
        file_size_mb=file_size_mb,
        duration=duration,
        media_type="video"
    )
    await state.set_state(UserStates.confirming_processing)

    await message.answer(
        get_video_settings_text(user_id, file_size_mb, duration),
        reply_markup=get_settings_keyboard(is_video=True),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "start_processing", UserStates.confirming_processing)
async def start_video_processing(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Start video processing"""
    user_id = callback.from_user.id
    data = await state.get_data()

    # Check if this is actually a video
    if data.get("media_type") != "video":
        return

    # Ensure user has settings
    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    settings = user_settings[user_id]

    try:
        await state.set_state(UserStates.processing_media)

        # Update message to show processing started
        await callback.message.edit_text(
            "🔄 <b>Processing your video...</b>\n\nExtracting frames and creating emojis. This may take a few minutes.",
            parse_mode="HTML"
        )
        await callback.answer()

        # Initialize file manager and config
        config = load_config()
        file_manager = FileManager(bot, config.max_file_size_mb)

        # Get file info and download
        file_info = await bot.get_file(data['file_id'])
        local_path = await file_manager.download_media(file_info, user_id)

        # Validate file
        validate_file_size(local_path, config.max_file_size_mb)
        media_type = validate_file_format(local_path)

        if media_type != "video":
            raise FileFormatError("Expected video file")

        # Validate video constraints
        video_processor.validate_video(local_path, config.max_video_duration)

        # Get video info
        video_info = video_processor.get_video_info(local_path)
        logger.info(f"Processing video: {video_info}")

        # Calculate processing steps
        estimated_frames = data.get('estimated_frames', 10)
        total_steps = 3 + estimated_frames + (estimated_frames * settings.grid_x * settings.grid_y)
        progress_tracker = ProgressTracker(total_steps)

        # Extract key frames from video
        progress_tracker.update(1, "Analyzing video...")
        max_frames = min(20, max(5, int(video_info['duration'] / 2))) if video_info['duration'] > 0 else 10

        frames = video_processor.extract_key_frames(
            local_path,
            max_frames=max_frames,
            progress_tracker=progress_tracker
        )

        logger.info(f"Extracted {len(frames)} frames from video")

        # Process each frame into emoji grids
        progress_tracker.update(1, "Processing frames...")

        all_emoji_files = []
        frame_sequences = []

        for frame_idx, frame in enumerate(frames):
            # Enhance frame
            frame = image_processor.enhance_image(frame, "medium")

            # Adapt frame to grid ratio
            adapted_frame = image_processor.adapt_image_to_grid(
                frame, settings.grid_x, settings.grid_y, settings.adaptation_method
            )

            # Split into grid cells
            emoji_cells = image_processor.split_image_grid(
                adapted_frame, settings.grid_x, settings.grid_y
            )

            frame_sequences.append(emoji_cells)
            progress_tracker.update(len(emoji_cells), f"Processed frame {frame_idx+1}/{len(frames)}")

        # Generate emoji packs for each frame
        progress_tracker.update(1, "Generating emoji packs...")

        output_dir = CACHE_DIR / f"user_{user_id}_video_output"
        output_dir.mkdir(exist_ok=True)

        for frame_idx, emoji_cells in enumerate(frame_sequences):
            pack_name = f"video_frame_{frame_idx+1:03d}"

            saved_files = emoji_generator.create_emoji_pack(
                emoji_cells, pack_name, user_id, output_dir / f"frame_{frame_idx+1:03d}"
            )
            all_emoji_files.extend(saved_files)

        # Create master ZIP archive with all frames
        master_zip_path = output_dir / f"video_emoji_pack_{user_id}.zip"
        emoji_generator.create_pack_archive(all_emoji_files, f"video_pack_{user_id}", master_zip_path)

        # Create Telegram sticker pack for first frame
        sticker_manager = StickerPackManager(bot)
        user_name = callback.from_user.first_name or "User"

        # Use first frame emojis for the sticker pack (Telegram has limits)
        first_frame_emojis = all_emoji_files[:settings.grid_x * settings.grid_y]

        pack_result = await sticker_manager.create_sticker_pack(
            user_id=user_id,
            user_name=user_name,
            emoji_files=first_frame_emojis,
            grid_size=(settings.grid_x, settings.grid_y),
            pack_type="video"
        )

        # Success message
        if pack_result["success"]:
            safe_title = pack_result["pack_title"].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            safe_link = pack_result["pack_link"]

            success_text = f"""
✅ <b>Video Processing Complete!</b>
⚠️ <i>BETA mode</i>

<b>Results:</b>
• Processed: {len(frames)} frames
• Created: {len(all_emoji_files)} emojis total
• Grid: {settings.grid_x}×{settings.grid_y} per frame

🎉 <b>Your Telegram custom emoji pack is ready!</b>
<i>(Using first frame as emoji pack)</i>

<b>Pack:</b> {safe_title}
<b>Link:</b> <a href="{safe_link}">{safe_link}</a>

Click the link above to add your custom emoji pack to Telegram!

<i>Note: Custom emojis require Telegram Premium to add.</i>
"""
        else:
            error_msg = pack_result.get("error", "Unknown error").replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            success_text = f"""
✅ <b>Video Processing Complete!</b>
⚠️ <i>BETA mode</i>

<b>Results:</b>
• Processed: {len(frames)} frames
• Created: {len(all_emoji_files)} emojis total
• Grid: {settings.grid_x}×{settings.grid_y} per frame

⚠️ <b>Custom emoji pack creation failed:</b> {error_msg}

You can still download the ZIP file with all your emojis below.
"""

        # Store results in state
        await state.update_data(
            emoji_files=[str(f) for f in all_emoji_files],
            zip_path=str(master_zip_path),
            pack_name=f"video_pack_{user_id}",
            frame_count=len(frames),
            frame_sequences=frame_sequences,
            sticker_pack_result=pack_result
        )

        await callback.message.edit_text(
            success_text,
            reply_markup=get_processing_complete_keyboard(has_sticker_pack=pack_result["success"]),
            parse_mode="HTML"
        )

        # Preview disabled by default - uncomment to enable
        # if frame_sequences:
        #     first_frame_files = all_emoji_files[:settings.grid_x * settings.grid_y]
        #     await send_video_emoji_preview(callback.message, first_frame_files, frame_idx=1)

        # Clean up original file
        try:
            local_path.unlink()
        except:
            pass

        # Log stickers created to database
        db.log_activity(user_id, "stickers_created", len(all_emoji_files))

        logger.info(f"Successfully processed video for user {user_id}: {len(frames)} frames, {len(all_emoji_files)} emojis")

    except Exception as e:
        logger.error(f"Video processing failed for user {user_id}: {e}")

        # Clean up any partially created files
        try:
            if 'local_path' in locals() and local_path and local_path.exists():
                local_path.unlink()

            output_dir = CACHE_DIR / f"user_{user_id}_video_output"
            if output_dir.exists():
                shutil.rmtree(output_dir)

        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup files after video processing error: {cleanup_error}")

        error_text = f"""
❌ <b>Video Processing Failed</b>

Error: {str(e)[:100]}

<b>Common issues:</b>
• Video too long (max 5 minutes)
• Unsupported format
• File corrupted

Please try with a shorter, high-quality video.
"""

        await callback.message.edit_text(
            error_text,
            parse_mode="HTML"
        )
        await state.clear()


async def send_video_emoji_preview(message: Message, emoji_files: list, frame_idx: int = 1, max_preview: int = 4):
    """Send preview of generated video emojis"""
    try:
        preview_files = emoji_files[:max_preview]

        if not preview_files:
            return

        await message.answer(f"📱 <b>Frame {frame_idx} Preview</b> (showing {len(preview_files)}/{len(emoji_files)} emojis):", parse_mode="HTML")

        for i, emoji_path in enumerate(preview_files):
            if Path(emoji_path).exists():
                try:
                    from aiogram.types import FSInputFile
                    await message.answer_photo(
                        FSInputFile(emoji_path),
                        caption=f"Frame {frame_idx} - Emoji {i+1}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to send video emoji preview {i+1}: {e}")

    except Exception as e:
        logger.warning(f"Failed to send video emoji preview: {e}")


@router.callback_query(F.data == "send_stickers")
async def send_video_stickers_by_frame(callback: CallbackQuery, state: FSMContext):
    """Send video emojis organized by frame"""
    data = await state.get_data()
    emoji_files = data.get('emoji_files', [])
    frame_count = data.get('frame_count', 0)

    # Only handle video files
    if frame_count == 0:
        return

    if not emoji_files:
        await callback.answer("❌ No emoji files found", show_alert=True)
        return

    await callback.answer("📱 Sending emojis by frame...")

    try:
        user_id = callback.from_user.id
        settings = user_settings.get(user_id)

        if not settings:
            await callback.message.answer("❌ Settings not found")
            return

        emojis_per_frame = settings.grid_x * settings.grid_y

        for frame_idx in range(frame_count):
            start_idx = frame_idx * emojis_per_frame
            end_idx = start_idx + emojis_per_frame
            frame_emojis = emoji_files[start_idx:end_idx]

            if frame_emojis:
                await callback.message.answer(f"🎬 <b>Frame {frame_idx + 1}/{frame_count}</b>", parse_mode="HTML")

                for i, emoji_path in enumerate(frame_emojis):
                    if Path(emoji_path).exists():
                        from aiogram.types import FSInputFile
                        await callback.message.answer_document(
                            FSInputFile(emoji_path),
                            caption=f"Frame {frame_idx + 1} - Emoji {i+1}/{len(frame_emojis)}"
                        )
                        await asyncio.sleep(0.3)

        await callback.message.answer("✅ All video emojis sent by frame!")

    except Exception as e:
        logger.error(f"Failed to send video stickers: {e}")
        await callback.message.answer("❌ Some emojis failed to send")


@router.callback_query(F.data == "create_animated", UserStates.confirming_processing)
async def show_animation_options(callback: CallbackQuery, state: FSMContext):
    """Show animation options for video processing"""
    await callback.message.edit_text(
        "🎬 <b>Animated Emoji Options</b>\n\n"
        "Configure your animated emoji settings:\n\n"
        "• <b>Frame Rate:</b> Higher FPS = smoother animation\n"
        "• <b>Duration:</b> How long each emoji loops\n"
        "• <b>File Size:</b> Each emoji must be under 64KB\n\n"
        "<i>Note: Animated emojis work in Telegram Premium</i>",
        reply_markup=get_animation_options_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fps_"), UserStates.confirming_processing)
async def set_animation_fps(callback: CallbackQuery, state: FSMContext):
    """Set animation FPS"""
    fps_value = int(callback.data.split("_")[1])
    await state.update_data(animation_fps=fps_value)
    await callback.answer(f"✅ Frame rate set to {fps_value} FPS")


@router.callback_query(F.data.startswith("duration_"), UserStates.confirming_processing)
async def set_animation_duration(callback: CallbackQuery, state: FSMContext):
    """Set animation duration"""
    duration_value = float(callback.data.split("_")[1])
    await state.update_data(animation_duration=duration_value)
    await callback.answer(f"✅ Duration set to {duration_value} seconds")


@router.callback_query(F.data == "confirm_animated", UserStates.confirming_processing)
async def start_animated_video_processing(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Start animated video processing"""
    user_id = callback.from_user.id

    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    settings = user_settings[user_id]
    data = await state.get_data()

    # Get animation settings or use defaults
    fps = data.get('animation_fps', 15)
    duration = data.get('animation_duration', 2.0)

    try:
        await state.set_state(UserStates.processing_media)

        await callback.message.edit_text(
            f"🎬 <b>Creating Animated Emojis...</b>\n\n"
            f"Settings: {fps} FPS, {duration}s duration\n\n"
            f"This will take several minutes for WebM encoding.",
            parse_mode="HTML"
        )
        await callback.answer()

        # Initialize processors
        config = load_config()
        file_manager = FileManager(bot, config.max_file_size_mb)

        # Get file info and download
        file_info = await bot.get_file(data['file_id'])
        local_path = await file_manager.download_media(file_info, user_id)

        # Validate file
        validate_file_size(local_path, config.max_file_size_mb)
        media_type = validate_file_format(local_path)

        if media_type != "video":
            raise FileFormatError("Expected video file")

        # Validate video constraints
        video_processor.validate_video(local_path, config.max_video_duration)

        # Get video info
        video_info = video_processor.get_video_info(local_path)
        logger.info(f"Processing animated video: {video_info}")

        # Calculate processing steps
        estimated_frames = min(int(fps * duration), data.get('estimated_frames', 10))
        total_steps = 5 + estimated_frames + (settings.grid_x * settings.grid_y)
        progress_tracker = ProgressTracker(total_steps)

        # Extract frames from video
        progress_tracker.update(1, "Extracting video frames...")
        frames = video_processor.extract_key_frames(
            local_path,
            max_frames=estimated_frames,
            progress_tracker=progress_tracker
        )

        logger.info(f"Extracted {len(frames)} frames for animation")

        # Process frames into grid sequences
        progress_tracker.update(1, "Processing frames...")
        frame_sequences = []

        for frame_idx, frame in enumerate(frames):
            # Enhance frame
            frame = image_processor.enhance_image(frame, "medium")

            # Adapt frame to grid ratio
            adapted_frame = image_processor.adapt_image_to_grid(
                frame, settings.grid_x, settings.grid_y, settings.adaptation_method
            )

            # Split into grid cells
            emoji_cells = image_processor.split_image_grid(
                adapted_frame, settings.grid_x, settings.grid_y
            )

            frame_sequences.append(emoji_cells)
            progress_tracker.update(1, f"Processed frame {frame_idx+1}/{len(frames)}")

        # Organize frames by emoji position
        progress_tracker.update(1, "Organizing animation sequences...")
        position_sequences = video_processor.organize_frames_by_position(
            frame_sequences, (settings.grid_x, settings.grid_y)
        )

        # Create animated emoji pack
        progress_tracker.update(1, "Creating animated emojis...")
        output_dir = CACHE_DIR / f"user_{user_id}_animated_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        pack_name = f"animated_emoji_pack_{user_id}"
        animated_files = emoji_generator.create_animated_emoji_pack(
            position_sequences,
            pack_name,
            user_id,
            output_dir,
            fps=fps,
            duration=duration,
            progress_tracker=progress_tracker
        )

        # Check if any animated files were actually created
        if not animated_files:
            raise VideoProcessingError(
                "No animated emojis were created. This could be due to:\n"
                "• FFmpeg VP9/VP8 codec not available\n"
                "• Video frames processing failed\n"
                "• All WebM files exceeded size limits"
            )

        # Create ZIP archive with animated files
        progress_tracker.update(1, "Creating archive...")
        zip_path = output_dir / f"{pack_name}.zip"
        emoji_generator.create_pack_archive(animated_files, pack_name, zip_path)

        # Create Telegram animated sticker pack
        sticker_manager = StickerPackManager(bot)
        user_name = callback.from_user.first_name or "User"

        # Use first few animated emojis for the sticker pack
        pack_emojis = animated_files[:min(20, len(animated_files))]

        pack_result = await sticker_manager.create_sticker_pack(
            user_id=user_id,
            user_name=user_name,
            emoji_files=pack_emojis,
            grid_size=(settings.grid_x, settings.grid_y),
            pack_type="animated",
            animated=True
        )

        # Success message
        if pack_result["success"]:
            safe_title = pack_result["pack_title"].replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            safe_link = pack_result["pack_link"]

            success_text = f"""
🎬 <b>Animated Emoji Processing Complete!</b>
⚠️ <i>BETA mode</i>

<b>Results:</b>
• Created: {len(animated_files)} animated emojis
• Grid: {settings.grid_x}×{settings.grid_y}
• Animation: {fps} FPS, {duration}s duration
• Format: WebM (Telegram compatible)

🎉 <b>Your animated emoji pack is ready!</b>

<b>Pack:</b> {safe_title}
<b>Link:</b> <a href="{safe_link}">{safe_link}</a>

Click the link above to add your animated emoji pack to Telegram!

<i>Note: Animated emojis require Telegram Premium to add and use.</i>
"""
        else:
            error_msg = pack_result.get("error", "Unknown error").replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            success_text = f"""
🎬 <b>Animated Emoji Processing Complete!</b>
⚠️ <i>BETA mode</i>

<b>Results:</b>
• Created: {len(animated_files)} animated emojis
• Grid: {settings.grid_x}×{settings.grid_y}
• Animation: {fps} FPS, {duration}s duration
• Format: WebM

⚠️ <b>Animated emoji pack creation failed:</b> {error_msg}

You can still download the ZIP file with your animated emojis below.
"""

        # Store results in state
        await state.update_data(
            emoji_files=[str(f) for f in animated_files],
            zip_path=str(zip_path),
            pack_name=pack_name,
            animated=True,
            fps=fps,
            duration=duration,
            sticker_pack_result=pack_result
        )

        await callback.message.edit_text(
            success_text,
            reply_markup=get_processing_complete_keyboard(
                has_sticker_pack=pack_result["success"],
                is_animated=True
            ),
            parse_mode="HTML"
        )

        # Preview disabled by default - uncomment to enable
        # if animated_files:
        #     await send_animated_emoji_preview(callback.message, animated_files[:3])

        # Clean up original file
        try:
            local_path.unlink()
        except:
            pass

        # Log stickers created to database
        db.log_activity(user_id, "stickers_created", len(animated_files))

        logger.info(f"Successfully created animated emoji pack for user {user_id}: {len(animated_files)} emojis")

    except Exception as e:
        logger.error(f"Animated video processing failed for user {user_id}: {e}")

        # Clean up any partially created files
        try:
            if 'local_path' in locals() and local_path and local_path.exists():
                local_path.unlink()

            output_dir = CACHE_DIR / f"user_{user_id}_animated_output"
            if output_dir.exists():
                shutil.rmtree(output_dir)

        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup files after animated processing error: {cleanup_error}")

        error_text = f"""
❌ <b>Animated Processing Failed</b>

Error: {str(e)[:100]}

<b>Common issues:</b>
• ffmpeg not installed (required for WebM)
• Video too long or complex
• Insufficient disk space for WebM encoding

Please try with a shorter video or use static mode.
"""

        await callback.message.edit_text(
            error_text,
            parse_mode="HTML"
        )
        await state.clear()


async def send_animated_emoji_preview(message: Message, animated_files: list, max_preview: int = 3):
    """Send preview of generated animated emojis"""
    try:
        preview_files = animated_files[:max_preview]

        if not preview_files:
            return

        await message.answer(f"🎬 <b>Animated Preview</b> (showing {len(preview_files)}/{len(animated_files)} emojis):", parse_mode="HTML")

        for i, emoji_path in enumerate(preview_files):
            if Path(emoji_path).exists():
                try:
                    from aiogram.types import FSInputFile
                    await message.answer_animation(
                        FSInputFile(emoji_path),
                        caption=f"Animated Emoji {i+1}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to send animated emoji preview {i+1}: {e}")
                    try:
                        await message.answer_document(
                            FSInputFile(emoji_path),
                            caption=f"Animated Emoji {i+1} (WebM)"
                        )
                    except Exception as e2:
                        logger.warning(f"Failed to send emoji as document {i+1}: {e2}")

    except Exception as e:
        logger.warning(f"Failed to send animated emoji preview: {e}")
