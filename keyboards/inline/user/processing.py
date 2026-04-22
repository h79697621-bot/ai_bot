from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_processing_complete_keyboard(has_sticker_pack: bool = False, is_animated: bool = False) -> InlineKeyboardMarkup:
    """Get processing complete keyboard"""
    keyboard = []

    if has_sticker_pack:
        emoji_text = "🎬 Add Animated Pack" if is_animated else "🎯 Add Emoji Pack"
        keyboard.append([
            InlineKeyboardButton(text=emoji_text, callback_data="add_sticker_pack")
        ])

    download_text = "💾 Download ZIP"
    individual_text = "📱 Send Individual"

    if is_animated:
        download_text = "💾 Download WebM Pack"
        individual_text = "🎬 Send Animated"

    keyboard.extend([
        [
            InlineKeyboardButton(text=download_text, callback_data="download_zip"),
            InlineKeyboardButton(text=individual_text, callback_data="send_stickers")
        ],
        [
            InlineKeyboardButton(text="🔄 Process Another", callback_data="process_another")
        ],
        [
            InlineKeyboardButton(text="🗑️ Delete Files", callback_data="delete_files")
        ]
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_animation_options_keyboard() -> InlineKeyboardMarkup:
    """Get animation options keyboard for video processing"""
    keyboard = [
        [
            InlineKeyboardButton(text="⚡ 15 FPS (Smooth)", callback_data="fps_15"),
            InlineKeyboardButton(text="🚀 30 FPS (Ultra)", callback_data="fps_30")
        ],
        [
            InlineKeyboardButton(text="⏱️ 1s Duration", callback_data="duration_1"),
            InlineKeyboardButton(text="⏱️ 2s Duration", callback_data="duration_2")
        ],
        [
            InlineKeyboardButton(text="⏱️ 3s Duration (Max)", callback_data="duration_3")
        ],
        [
            InlineKeyboardButton(text="✅ Create Animated", callback_data="confirm_animated"),
            InlineKeyboardButton(text="📱 Static Mode", callback_data="start_processing")
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings"),
            InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
