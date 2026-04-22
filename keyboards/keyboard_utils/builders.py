from typing import List, Optional, Union
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def build_inline_keyboard(
    buttons: List[List[dict]], 
    row_width: int = 2
) -> InlineKeyboardMarkup:
    """
    Build inline keyboard from button data
    
    Args:
        buttons: List of button rows, each row contains button dicts with 'text' and 'callback_data'
        row_width: Number of buttons per row when auto-arranging
        
    Returns:
        InlineKeyboardMarkup object
    """
    keyboard = []
    
    for row in buttons:
        button_row = []
        for btn_data in row:
            button = InlineKeyboardButton(
                text=btn_data['text'],
                callback_data=btn_data.get('callback_data'),
                url=btn_data.get('url'),
                switch_inline_query=btn_data.get('switch_inline_query'),
                switch_inline_query_current_chat=btn_data.get('switch_inline_query_current_chat')
            )
            button_row.append(button)
        keyboard.append(button_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_reply_keyboard(
    buttons: List[str], 
    row_width: int = 2,
    resize_keyboard: bool = True,
    one_time_keyboard: bool = False
) -> ReplyKeyboardMarkup:
    """
    Build reply keyboard from button texts
    
    Args:
        buttons: List of button texts
        row_width: Number of buttons per row
        resize_keyboard: Whether to resize keyboard
        one_time_keyboard: Whether to hide keyboard after use
        
    Returns:
        ReplyKeyboardMarkup object
    """
    keyboard = []
    
    # Split buttons into rows
    for i in range(0, len(buttons), row_width):
        row = [KeyboardButton(text=text) for text in buttons[i:i + row_width]]
        keyboard.append(row)
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=resize_keyboard,
        one_time_keyboard=one_time_keyboard
    )


def create_grid_size_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for grid size selection"""
    buttons = [
        [
            {'text': '1×3 Horizontal', 'callback_data': 'grid_1_3'},
            {'text': '3×1 Vertical', 'callback_data': 'grid_3_1'}
        ],
        [
            {'text': '2×2 Square', 'callback_data': 'grid_2_2'},
            {'text': '3×3 Square', 'callback_data': 'grid_3_3'}
        ],
        [
            {'text': '2×5 Wide', 'callback_data': 'grid_2_5'},
            {'text': '5×2 Tall', 'callback_data': 'grid_5_2'}
        ],
        [
            {'text': '4×4 Large', 'callback_data': 'grid_4_4'},
            {'text': '🔧 Custom', 'callback_data': 'grid_custom'}
        ],
        [
            {'text': '⚙️ Settings', 'callback_data': 'settings'},
            {'text': '❌ Cancel', 'callback_data': 'cancel'}
        ]
    ]
    
    return build_inline_keyboard(buttons)


def create_adaptation_method_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for adaptation method selection"""
    buttons = [
        [
            {'text': '📏 Pad (Recommended)', 'callback_data': 'adapt_pad'},
        ],
        [
            {'text': '↔️ Stretch', 'callback_data': 'adapt_stretch'},
        ],
        [
            {'text': '✂️ Crop', 'callback_data': 'adapt_crop'},
        ],
        [
            {'text': '🔙 Back', 'callback_data': 'back_to_grid'},
            {'text': '❌ Cancel', 'callback_data': 'cancel'}
        ]
    ]
    
    return build_inline_keyboard(buttons)


def create_processing_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for processing confirmation"""
    buttons = [
        [
            {'text': '✅ Start Processing', 'callback_data': 'start_processing'},
        ],
        [
            {'text': '👁️ Preview', 'callback_data': 'preview_adaptation'},
            {'text': '⚙️ Settings', 'callback_data': 'settings'}
        ],
        [
            {'text': '❌ Cancel', 'callback_data': 'cancel'}
        ]
    ]
    
    return build_inline_keyboard(buttons)


def create_settings_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for bot settings"""
    buttons = [
        [
            {'text': '📐 Grid Size', 'callback_data': 'set_grid_size'},
            {'text': '🔄 Adaptation Method', 'callback_data': 'set_adaptation'}
        ],
        [
            {'text': '🎨 Quality Settings', 'callback_data': 'set_quality'},
            {'text': '🔍 Background Removal', 'callback_data': 'set_background'}
        ],
        [
            {'text': '📊 Statistics', 'callback_data': 'show_stats'},
            {'text': '🆘 Help', 'callback_data': 'show_help'}
        ],
        [
            {'text': '🔙 Back', 'callback_data': 'back_to_main'},
            {'text': '❌ Close', 'callback_data': 'cancel'}
        ]
    ]
    
    return build_inline_keyboard(buttons)


def create_quality_settings_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for quality settings"""
    buttons = [
        [
            {'text': '🔴 High Quality', 'callback_data': 'quality_high'},
            {'text': '🟡 Medium Quality', 'callback_data': 'quality_medium'}
        ],
        [
            {'text': '🟢 Low Quality (Fast)', 'callback_data': 'quality_low'},
        ],
        [
            {'text': '🔙 Back', 'callback_data': 'settings'},
            {'text': '❌ Cancel', 'callback_data': 'cancel'}
        ]
    ]
    
    return build_inline_keyboard(buttons)


def create_cancel_keyboard() -> InlineKeyboardMarkup:
    """Create simple cancel keyboard"""
    buttons = [
        [
            {'text': '❌ Cancel', 'callback_data': 'cancel'}
        ]
    ]
    
    return build_inline_keyboard(buttons)