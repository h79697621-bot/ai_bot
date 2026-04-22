from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_grid_size_keyboard() -> InlineKeyboardMarkup:
    """Get grid size selection keyboard (used after image upload)"""
    keyboard = [
        [
            InlineKeyboardButton(text="1×3 📏", callback_data="grid_1_3"),
            InlineKeyboardButton(text="3×1 📐", callback_data="grid_3_1")
        ],
        [
            InlineKeyboardButton(text="2×2 ⬜", callback_data="grid_2_2"),
            InlineKeyboardButton(text="3×3 ⬛", callback_data="grid_3_3")
        ],
        [
            InlineKeyboardButton(text="2×5 ↔️", callback_data="grid_2_5"),
            InlineKeyboardButton(text="5×2 ↕️", callback_data="grid_5_2")
        ],
        [
            InlineKeyboardButton(text="4×4 🔲", callback_data="grid_4_4"),
            InlineKeyboardButton(text="🔧 Custom", callback_data="grid_custom")
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
