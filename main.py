import asyncio
import logging
import sqlite3
import aiohttp

from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
)
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

API_TOKEN = "8614544546:AAEiDB080jmjjYQPRsongRt2UcelwUw7heg"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ===== БАЗА =====
conn = sqlite3.connect('shop_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    item_type TEXT,
    item_name TEXT,
    payment_method TEXT,
    status TEXT,
    created_at TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
''')

conn.commit()

def set_setting(key, value):
    cursor.execute('INSERT OR REPLACE INTO settings VALUES (?, ?)', (key, value))
    conn.commit()

def get_setting(key):
    cursor.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = cursor.fetchone()
    return row[0] if row else None

def save_order(user_id, item_type, item_name, payment_method):
    cursor.execute(
        'INSERT INTO orders VALUES (NULL,?,?,?,?,?,?)',
        (user_id, item_type, item_name, payment_method, "paid",
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

# ===== НАСТРОЙКИ =====
ADMIN_IDS = [8364328997]
SELLER_USERNAME = "vorrxy"
waiting_for_emoji = set()

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ===== МЕНЮ =====
def main_menu(user_id):
    kb = [
        [InlineKeyboardButton(text="Купить звезды", callback_data="stars_menu")],
        [InlineKeyboardButton(text="Аккаунты", callback_data="accounts_menu")],
        [InlineKeyboardButton(text="Подарки", callback_data="gifts_menu")]
    ]
    if is_admin(user_id):
        kb.append([InlineKeyboardButton(text="Админ панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ===== СТАРТ =====
@dp.message(Command("start"))
async def start(message: Message):
    emoji_id = get_setting("welcome_emoji")

    text = f"Здравствуйте, {message.from_user.first_name}!"

    if emoji_id:
        text = f"<tg-emoji emoji-id='{emoji_id}'></tg-emoji> " + text

    await message.answer(text, reply_markup=main_menu(message.from_user.id))

# ===== НАЗАД =====
@dp.callback_query(F.data == "back_to_menu")
async def back(callback: CallbackQuery):
    await callback.message.edit_text(
        f"Здравствуйте, {callback.from_user.first_name}!",
        reply_markup=main_menu(callback.from_user.id)
    )
    await callback.answer()

# ===== ЗВЕЗДЫ =====
@dp.callback_query(F.data == "stars_menu")
async def stars(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 (65 руб)", callback_data="buy_50")],
        [InlineKeyboardButton(text="100 (130 руб)", callback_data="buy_100")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text("Выберите количество", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy(callback: CallbackQuery):
    stars = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"Покупка {stars} звезд\nСвязь: @{SELLER_USERNAME}"
    )
    await callback.answer()

# ===== АККАУНТЫ =====
@dp.callback_query(F.data == "accounts_menu")
async def accounts(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Индонезия", callback_data="country_indonesia")],
        [InlineKeyboardButton(text="Индия", callback_data="country_india")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text("Выберите страну", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("country_"))
async def country(callback: CallbackQuery):
    country = callback.data.split("_")[1]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить за 40 руб", callback_data=f"buy_acc_rub_{country}")],
        [InlineKeyboardButton(text="Купить за 30 звезд", callback_data=f"buy_acc_star_{country}")],
        [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
    ])

    await callback.message.edit_text("Выберите оплату", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_acc_star_"))
async def buy_acc_star(callback: CallbackQuery):
    country = callback.data.split("_")[3]

    prices = [LabeledPrice(label="Аккаунт", amount=30)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Покупка аккаунта",
        description="Доступ",
        payload=f"account_{country}",
        currency="XTR",
        prices=prices,
        provider_token=""
    )

# ===== ПОДАРКИ =====
async def get_gifts():
    url = f"https://api.telegram.org/bot{API_TOKEN}/getStarGiftOptions"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get("result", [])

@dp.callback_query(F.data == "gifts_menu")
async def gifts(callback: CallbackQuery):
    gifts = await get_gifts()
    dp["gifts"] = gifts

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=g.get("name"), callback_data=f"gift_{i}")]
        for i, g in enumerate(gifts[:10])
    ] + [[InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]])

    await callback.message.edit_text("Список подарков", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("gift_"))
async def gift_detail(callback: CallbackQuery):
    gifts = dp.get("gifts", [])
    i = int(callback.data.split("_")[1])

    gift = gifts[i]
    animation_url = gift.get("animation_url")

    await callback.message.delete()

    await callback.message.answer_animation(
        animation=animation_url,
        caption="Аренда 7 дней за 15 звезд",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить", callback_data=f"pay_{i}")]
        ])
    )

# ===== ОПЛАТА =====
@dp.callback_query(F.data.startswith("pay_"))
async def pay(callback: CallbackQuery):
    i = int(callback.data.split("_")[1])

    prices = [LabeledPrice(label="Подарок", amount=15)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Аренда подарка",
        description="7 дней",
        payload=f"gift_{i}",
        currency="XTR",
        prices=prices,
        provider_token=""
    )

@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def success(message: Message):
    await message.answer("Оплата прошла успешно")

# ===== АДМИН =====
@dp.callback_query(F.data == "admin_panel")
async def admin(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Установить эмодзи", callback_data="set_emoji")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text("Админ панель", reply_markup=kb)

@dp.callback_query(F.data == "set_emoji")
async def set_emoji(callback: CallbackQuery):
    waiting_for_emoji.add(callback.from_user.id)
    await callback.message.answer("Отправь премиум эмодзи")

@dp.message(F.entities)
async def save_emoji(message: Message):
    if message.from_user.id not in waiting_for_emoji:
        return

    for e in message.entities:
        if e.type == "custom_emoji":
            set_setting("welcome_emoji", e.custom_emoji_id)
            waiting_for_emoji.remove(message.from_user.id)
            await message.answer("Сохранено")
            return

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
