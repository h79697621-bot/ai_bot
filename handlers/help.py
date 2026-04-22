import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from keyboards import get_help_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("help"))
@router.message(F.text == "🆘 Help")
async def help_command(message: Message):
    """Handle /help command"""
    help_text = """
🆘 <b>Emoji Pack Bot Help</b>

<b>How to Use:</b>
1. Send an image or video
2. Adjust grid size and adaptation settings
3. Click "Done" to process
4. Get your emoji pack!

<b>Grid Sizes:</b>
• <code>1×3</code> - Timeline/progress bars
• <code>3×1</code> - Tall subjects/portraits
• <code>2×2</code> - Basic 4-emoji pack
• <code>3×3</code> - Classic 9-emoji pack
• <code>2×5</code> - Wide scenes/landscapes
• Custom - Any size up to 8×8

<b>Adaptation Methods:</b>
• <code>Pad</code> - Adds borders, keeps everything
• <code>Stretch</code> - Changes proportions
• <code>Crop</code> - Cuts edges, focuses center

<b>Commands:</b>
/start - Start the bot
/help - Show this help
/settings - Open settings menu

Need more help? Use the buttons below!
"""

    await message.answer(
        help_text,
        reply_markup=get_help_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "help_quickstart")
async def help_quickstart(callback: CallbackQuery):
    """Quick start guide"""
    text = """
🚀 <b>Quick Start Guide</b>

<b>Step 1: Send Media</b>
• Just send an image or video to the bot
• Supported: JPG, PNG, WebP, MP4, MOV

<b>Step 2: Choose Settings</b>
• Grid Size: How many emojis to create
• Adaptation: How to fit your image

<b>Step 3: Process</b>
• Click "Done - Process Image"
• Wait for processing to complete

<b>Step 4: Get Results</b>
• Add the emoji pack to Telegram
• Or download as ZIP file

<b>Pro Tip:</b> Start with a 2×2 grid and "Pad" adaptation for best results!
"""

    await callback.message.edit_text(text, reply_markup=get_help_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help_grid")
async def help_grid(callback: CallbackQuery):
    """Grid size guide"""
    text = """
📐 <b>Grid Size Guide</b>

<b>Common Sizes:</b>
• <code>1×3</code> - Perfect for progress bars, timelines
• <code>3×1</code> - Great for tall objects, portraits
• <code>2×2</code> - Simple 4-piece puzzles
• <code>3×3</code> - Classic grid, most versatile
• <code>4×4</code> - Detailed images, 16 emojis

<b>Custom Sizes:</b>
• Any combination from 1×1 to 8×8
• Examples: 1×5, 2×7, 6×2, etc.

<b>Choosing the Right Size:</b>
• More cells = more detail
• Fewer cells = simpler, clearer emojis
• Match your image's aspect ratio

<b>Tips:</b>
• Wide images → Use 1×X or 2×X grids
• Tall images → Use X×1 or X×2 grids
• Square images → Use X×X grids
"""

    await callback.message.edit_text(text, reply_markup=get_help_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help_adaptation")
async def help_adaptation(callback: CallbackQuery):
    """Adaptation method guide"""
    text = """
🔄 <b>Adaptation Method Guide</b>

<b>Pad (Recommended) 📏</b>
• Adds white borders to fit grid ratio
• Keeps all original content
• Best for: Most images, beginners
• Result: No distortion, complete image

<b>Stretch ↔️</b>
• Changes image proportions
• Fits exactly to grid ratio
• Best for: Abstract images, patterns
• Result: May look distorted

<b>Crop ✂️</b>
• Cuts edges to fit grid ratio
• Focuses on center content
• Best for: Images with important centers
• Result: May lose edge content

<b>When to Use What:</b>
• Portrait photo → Pad or Crop
• Landscape photo → Pad
• Logo/text → Pad
• Pattern/texture → Stretch
• Face/person → Crop (focuses on face)
"""

    await callback.message.edit_text(text, reply_markup=get_help_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help_tips")
async def help_tips(callback: CallbackQuery):
    """Tips and tricks"""
    text = """
💡 <b>Tips & Tricks</b>

<b>Image Quality:</b>
• Use high-resolution images (1000×1000+)
• Avoid very blurry or dark images
• PNG files preserve quality better

<b>Grid Selection:</b>
• Start small (2×2) for testing
• Match image orientation
• More cells = longer processing time

<b>Adaptation Tips:</b>
• Use Pad for text/logos (keeps readability)
• Use Crop for faces (centers on subject)

<b>Video Processing:</b> ⚠️ <i>BETA</i>
• Keep videos under 2 minutes for best results
• Good lighting improves frame quality
• Bot automatically picks best frames

<b>Telegram Stickers:</b>
• Each emoji is 512×512 pixels
• PNG format with transparency
• Perfect for Telegram sticker packs!
"""

    await callback.message.edit_text(text, reply_markup=get_help_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help_faq")
async def help_faq(callback: CallbackQuery):
    """Frequently asked questions"""
    text = """
❓ <b>Frequently Asked Questions</b>

<b>Q: What file formats are supported?</b>
A: Images: JPG, PNG, WebP, BMP
   Videos: MP4, AVI, MOV, WebM

<b>Q: What's the maximum file size?</b>
A: 50MB for images and videos

<b>Q: How long does processing take?</b>
A: Usually 10-60 seconds depending on size

<b>Q: Can I use the emojis commercially?</b>
A: Yes, but ensure you have rights to original image

<b>Q: Why is my image blurry?</b>
A: Try higher resolution input or smaller grid size

<b>Q: Bot not responding?</b>
A: Try /start to reset

<b>Q: How to create animated emojis?</b>
A: Send a video - bot extracts frames automatically ⚠️ <i>BETA</i>

<b>Q: Where are my files stored?</b>
A: Temporarily cached, auto-deleted after 1 hour
"""

    await callback.message.edit_text(text, reply_markup=get_help_keyboard(), parse_mode="HTML")
    await callback.answer()
