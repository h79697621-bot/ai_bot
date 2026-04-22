from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_settings_keyboard(is_video: bool = False) -> InlineKeyboardMarkup:
    """Get main settings keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="📐 Grid Size", callback_data="set_grid_size"),
            InlineKeyboardButton(text="🔄 Adaptation", callback_data="set_adaptation")
        ],
        [
            InlineKeyboardButton(text="🎨 Background", callback_data="set_background")
        ],
        [
            InlineKeyboardButton(text="🆘 Help", callback_data="show_help")
        ],
        [
            InlineKeyboardButton(text="✅ Done - Process", callback_data="start_processing")
        ]
    ]

    if is_video:
        keyboard.insert(-1, [
            InlineKeyboardButton(text="🎬 Create Animated", callback_data="create_animated")
        ])

    keyboard.append([
        InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_grid_selection_keyboard() -> InlineKeyboardMarkup:
    """Get grid size selection keyboard"""
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


def get_adaptation_keyboard() -> InlineKeyboardMarkup:
    """Get adaptation method selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="📏 Pad (Keep All)", callback_data="adapt_pad"),
        ],
        [
            InlineKeyboardButton(text="↔️ Stretch (Distort)", callback_data="adapt_stretch"),
        ],
        [
            InlineKeyboardButton(text="✂️ Crop (Cut Edges)", callback_data="adapt_crop"),
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_background_keyboard() -> InlineKeyboardMarkup:
    """Get background removal selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="🖼️ Keep Original", callback_data="bg_keep"),
        ],
        [
            InlineKeyboardButton(text="⬜ Remove White BG", callback_data="bg_remove_white"),
        ],
        [
            InlineKeyboardButton(text="⬛ Remove Black BG", callback_data="bg_remove_black"),
        ],
        [
            InlineKeyboardButton(text="🪄 Smart Removal", callback_data="bg_remove_smart"),
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Get help keyboard - simplified"""
    keyboard = [
        [
            InlineKeyboardButton(text="🚀 Quick Start", callback_data="help_quickstart"),
            InlineKeyboardButton(text="📐 Grid Guide", callback_data="help_grid")
        ],
        [
            InlineKeyboardButton(text="🔄 Adaptation Guide", callback_data="help_adaptation"),
            InlineKeyboardButton(text="💡 Tips", callback_data="help_tips")
        ],
        [
            InlineKeyboardButton(text="❓ FAQ", callback_data="help_faq")
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="back_to_settings")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
