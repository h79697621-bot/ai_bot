import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import load_config
from database import db

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    config = load_config()
    return user_id == config.admin_user_id


@router.message(Command("admin"))
async def admin_command(message: Message):
    """Handle /admin command - show statistics"""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("⛔ Access denied. This command is for admins only.")
        return

    # Get statistics
    stats = db.get_statistics()

    # Format last users
    last_users_text = ""
    for i, user in enumerate(stats["last_users"], 1):
        name = user["first_name"] or "Unknown"
        if user["last_name"]:
            name += f" {user['last_name']}"
        username = f"@{user['username']}" if user["username"] else "no username"
        last_users_text += f"\n   {i}. {name} ({username}) - ID: <code>{user['user_id']}</code>"
        last_users_text += f"\n      Stickers: {user['stickers_created']} | Last seen: {user['last_seen'][:16]}"

    if not last_users_text:
        last_users_text = "\n   No users yet"

    admin_text = f"""
📊 <b>Admin Statistics Panel</b>

<b>General:</b>
• Total stickers made: <b>{stats['total_stickers']}</b>
• Unique users: <b>{stats['unique_users']}</b>
• Stickers made last 24h: <b>{stats['stickers_24h']}</b>

<b>Active Users:</b>
• Last 24 hours: <b>{stats['active_24h']}</b>
• Last 7 days: <b>{stats['active_week']}</b>
• Last 30 days: <b>{stats['active_month']}</b>

<b>Last 3 Users:</b>{last_users_text}
"""

    await message.answer(admin_text, parse_mode="HTML")
