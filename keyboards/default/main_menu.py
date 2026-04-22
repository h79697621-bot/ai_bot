from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    """Get main menu keyboard"""
    keyboard = [
        [
            KeyboardButton(text="📐 Set Grid Size"),
            KeyboardButton(text="🔄 Adaptation Method")
        ],
        [
            KeyboardButton(text="⚙️ Settings"),
            KeyboardButton(text="🆘 Help")
        ],
        [
            KeyboardButton(text="📊 My Stats"),
            KeyboardButton(text="📋 Examples")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_processing_menu() -> ReplyKeyboardMarkup:
    """Get processing menu keyboard"""
    keyboard = [
        [
            KeyboardButton(text="🖼️ Send Image"),
            KeyboardButton(text="🎥 Send Video")
        ],
        [
            KeyboardButton(text="❌ Cancel Processing")
        ]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )