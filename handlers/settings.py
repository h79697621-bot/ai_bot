import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards import (
    get_settings_keyboard, get_grid_selection_keyboard, get_adaptation_keyboard,
    get_background_keyboard, get_help_keyboard
)
from states import UserStates
from .start import user_settings

logger = logging.getLogger(__name__)
router = Router()

# Background mode display names
BG_MODE_NAMES = {
    "keep": "Keep Original",
    "remove_white": "Remove White",
    "remove_black": "Remove Black",
    "remove_smart": "Smart Removal"
}


def get_settings_text(user_id: int, is_media_uploaded: bool = False, media_type: str = None) -> str:
    """Generate settings text for a user"""
    settings = user_settings.get(user_id)
    if not settings:
        return "No settings configured yet."

    method_names = {"pad": "Pad (Keep All)", "stretch": "Stretch", "crop": "Crop"}
    bg_name = BG_MODE_NAMES.get(settings.background_mode, settings.background_mode)

    if is_media_uploaded:
        media_icon = "🎥" if media_type == "video" else "🖼️"
        beta_text = "\n⚠️ <i>Video processing is in BETA mode</i>" if media_type == "video" else ""
        header = f"{media_icon} <b>Media Received!</b>{beta_text}"
    else:
        header = "⚙️ <b>Settings</b>"

    return f"""
{header}

<b>Current Settings:</b>
• Grid Size: {settings.grid_x}×{settings.grid_y}
• Adaptation: {method_names.get(settings.adaptation_method, settings.adaptation_method)}
• Background: {bg_name}

<b>Total emojis:</b> {settings.grid_x * settings.grid_y}

{"Adjust settings if needed, then click 'Done' to process." if is_media_uploaded else "Configure your settings, then send an image or video."}
"""


async def get_state_info(state: FSMContext):
    """Get current state info to determine if media is uploaded"""
    current_state = await state.get_state()
    data = await state.get_data()
    # Check if media is uploaded - either by state or by presence of file_id in data
    is_media_uploaded = (
        current_state == UserStates.confirming_processing.state or
        data.get("file_id") is not None
    )
    media_type = data.get("media_type") if is_media_uploaded else None
    return is_media_uploaded, media_type


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Settings")
async def settings_command(message: Message, state: FSMContext):
    """Handle /settings command"""
    user_id = message.from_user.id

    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    is_media_uploaded, media_type = await get_state_info(state)

    await message.answer(
        get_settings_text(user_id, is_media_uploaded, media_type),
        reply_markup=get_settings_keyboard(is_video=(media_type == "video")),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery, state: FSMContext):
    """Handle settings menu callback"""
    user_id = callback.from_user.id

    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    is_media_uploaded, media_type = await get_state_info(state)

    await callback.message.edit_text(
        get_settings_text(user_id, is_media_uploaded, media_type),
        reply_markup=get_settings_keyboard(is_video=(media_type == "video")),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings(callback: CallbackQuery, state: FSMContext):
    """Go back to settings menu"""
    user_id = callback.from_user.id

    is_media_uploaded, media_type = await get_state_info(state)

    await callback.message.edit_text(
        get_settings_text(user_id, is_media_uploaded, media_type),
        reply_markup=get_settings_keyboard(is_video=(media_type == "video")),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_grid_size")
async def set_grid_size(callback: CallbackQuery, state: FSMContext):
    """Handle grid size setting"""
    user_id = callback.from_user.id
    settings = user_settings.get(user_id)

    current_grid = f"{settings.grid_x}×{settings.grid_y}" if settings else "2×2"

    text = f"""
📐 <b>Grid Size Configuration</b>

Current: <code>{current_grid}</code>

Choose a grid size or select "Custom" to enter your own:
"""

    await callback.message.edit_text(
        text,
        reply_markup=get_grid_selection_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_adaptation")
async def set_adaptation(callback: CallbackQuery, state: FSMContext):
    """Handle adaptation method setting"""
    user_id = callback.from_user.id
    settings = user_settings.get(user_id)

    current_method = settings.adaptation_method if settings else "pad"
    method_names = {"pad": "Pad", "stretch": "Stretch", "crop": "Crop"}

    text = f"""
🔄 <b>Adaptation Method</b>

Current: <code>{method_names.get(current_method, current_method)}</code>

How should the image be adapted to fit the grid?

• <b>Pad</b> - Adds borders, keeps everything visible
• <b>Stretch</b> - Changes proportions to fit exactly
• <b>Crop</b> - Cuts edges, focuses on center
"""

    await callback.message.edit_text(
        text,
        reply_markup=get_adaptation_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_background")
async def set_background(callback: CallbackQuery, state: FSMContext):
    """Handle background removal setting"""
    user_id = callback.from_user.id
    settings = user_settings.get(user_id)

    current_mode = settings.background_mode if settings else "keep"
    mode_name = BG_MODE_NAMES.get(current_mode, current_mode)

    text = f"""
🎨 <b>Background Removal</b>

Current: <code>{mode_name}</code>

Choose how to handle the background:

• <b>Keep Original</b> - No changes to background
• <b>Remove White</b> - Make white areas transparent
• <b>Remove Black</b> - Make black areas transparent
• <b>Smart Removal</b> - Auto-detect and remove background
"""

    await callback.message.edit_text(
        text,
        reply_markup=get_background_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "show_help")
async def show_help(callback: CallbackQuery):
    """Show help menu"""
    text = """
🆘 <b>Help</b>

Choose a topic to learn more:
"""

    await callback.message.edit_text(
        text,
        reply_markup=get_help_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# Grid size handlers
@router.callback_query(F.data.startswith("grid_"))
async def handle_grid_selection(callback: CallbackQuery, state: FSMContext):
    """Handle grid size selection"""
    user_id = callback.from_user.id

    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    data = callback.data

    # Get state info to preserve it
    is_media_uploaded, media_type = await get_state_info(state)

    if data == "grid_custom":
        # Store current state info before changing state
        state_data = await state.get_data()
        await state.set_state(UserStates.setting_grid_size_x)
        # Preserve the media data
        await state.update_data(**state_data)

        await callback.message.edit_text(
            "🔧 <b>Custom Grid Size</b>\n\nPlease send your custom grid size in format: <code>X Y</code>\nExample: <code>4 3</code> for 4×3 grid\n\n(Values must be between 1 and 8)",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # Parse grid size from callback data
    parts = data.split("_")
    if len(parts) >= 3:
        try:
            grid_x = int(parts[1])
            grid_y = int(parts[2])

            user_settings[user_id].grid_x = grid_x
            user_settings[user_id].grid_y = grid_y

            await callback.message.edit_text(
                get_settings_text(user_id, is_media_uploaded, media_type),
                reply_markup=get_settings_keyboard(is_video=(media_type == "video")),
                parse_mode="HTML"
            )
            await callback.answer(f"Grid size set to {grid_x}×{grid_y}")

        except ValueError:
            await callback.answer("Invalid grid size format", show_alert=True)


# Adaptation method handlers
@router.callback_query(F.data.startswith("adapt_"))
async def handle_adaptation_selection(callback: CallbackQuery, state: FSMContext):
    """Handle adaptation method selection"""
    user_id = callback.from_user.id

    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    method = callback.data.split("_")[1]
    user_settings[user_id].adaptation_method = method

    method_names = {"pad": "Pad", "stretch": "Stretch", "crop": "Crop"}
    method_name = method_names.get(method, method)

    is_media_uploaded, media_type = await get_state_info(state)

    await callback.message.edit_text(
        get_settings_text(user_id, is_media_uploaded, media_type),
        reply_markup=get_settings_keyboard(is_video=(media_type == "video")),
        parse_mode="HTML"
    )
    await callback.answer(f"Adaptation set to {method_name}")


# Background mode handlers
@router.callback_query(F.data.startswith("bg_"))
async def handle_background_selection(callback: CallbackQuery, state: FSMContext):
    """Handle background mode selection"""
    user_id = callback.from_user.id

    if user_id not in user_settings:
        from models import UserSettings
        user_settings[user_id] = UserSettings(user_id=user_id)

    # Parse mode from callback data (bg_keep, bg_remove_white, etc.)
    mode = callback.data[3:]  # Remove "bg_" prefix
    user_settings[user_id].background_mode = mode

    mode_name = BG_MODE_NAMES.get(mode, mode)

    is_media_uploaded, media_type = await get_state_info(state)

    await callback.message.edit_text(
        get_settings_text(user_id, is_media_uploaded, media_type),
        reply_markup=get_settings_keyboard(is_video=(media_type == "video")),
        parse_mode="HTML"
    )
    await callback.answer(f"Background set to {mode_name}")


# Handler for "Done - Process" when no image is uploaded
@router.callback_query(F.data == "start_processing")
async def start_processing_no_image(callback: CallbackQuery, state: FSMContext):
    """Handle start_processing when no image has been uploaded"""
    # This handler catches start_processing clicks when NOT in confirming_processing state
    # (the image.py and video.py handlers have state filters, so this catches the rest)
    await callback.answer("Please send an image or video first!", show_alert=True)


# Navigation handlers
@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Cancel current action and clear state"""
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Cancelled</b>\n\nSend me an image or video when you're ready to try again.",
        parse_mode="HTML"
    )
    await callback.answer("Cancelled")


# Handle custom grid size input
@router.message(F.text.regexp(r'^\d+\s+\d+$'), UserStates.setting_grid_size_x)
async def handle_custom_grid_input(message: Message, state: FSMContext):
    """Handle custom grid size input"""
    user_id = message.from_user.id

    try:
        parts = message.text.split()
        grid_x, grid_y = int(parts[0]), int(parts[1])

        if not (1 <= grid_x <= 8 and 1 <= grid_y <= 8):
            await message.answer("❌ Grid size must be between 1×1 and 8×8")
            return

        if user_id not in user_settings:
            from models import UserSettings
            user_settings[user_id] = UserSettings(user_id=user_id)

        user_settings[user_id].grid_x = grid_x
        user_settings[user_id].grid_y = grid_y

        # Check if there was media uploaded before
        data = await state.get_data()
        has_media = data.get("file_id") is not None
        media_type = data.get("media_type")

        if has_media:
            # Restore confirming_processing state
            await state.set_state(UserStates.confirming_processing)
        else:
            await state.clear()

        await message.answer(
            get_settings_text(user_id, has_media, media_type),
            reply_markup=get_settings_keyboard(is_video=(media_type == "video")),
            parse_mode="HTML"
        )

    except (ValueError, IndexError):
        await message.answer("❌ Invalid format. Please use: <code>X Y</code> (e.g., <code>4 3</code>)", parse_mode="HTML")


# Handle invalid input during custom grid state
@router.message(UserStates.setting_grid_size_x)
async def handle_invalid_grid_input(message: Message):
    """Handle invalid custom grid input"""
    await message.answer(
        "❌ Invalid format. Please enter two numbers separated by space.\n\nExample: <code>4 3</code> for a 4×3 grid",
        parse_mode="HTML"
    )
