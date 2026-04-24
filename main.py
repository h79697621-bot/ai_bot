import asyncio
import logging
import sqlite3
import os
import aiohttp
import json

from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton,
    InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
)
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("8614544546:AAEiDB080jmjjYQPRsongRt2UcelwUw7heg")

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
conn.commit()

def save_order(user_id, item_type, item_name, payment_method):
    cursor.execute(
        'INSERT INTO orders (user_id, item_type, item_name, payment_method, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, item_type, item_name, payment_method, "paid",
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

# ===== НАСТРОЙКИ =====
ADMIN_IDS = [8364328997]
SELLER_USERNAME = "vorrxy"

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ===== КНОПКИ =====
def main_menu(user_id):
    kb = [
        [InlineKeyboardButton(text="⭐ Купить звезды", callback_data="stars_menu")],
        [InlineKeyboardButton(text="🌍 Аккаунты", callback_data="accounts_menu")],
        [InlineKeyboardButton(text="🎁 Подарки", callback_data="gifts_menu")]
    ]
    if is_admin(user_id):
        kb.append([InlineKeyboardButton(text="👑 Админ панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def stars_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 ⭐ (65 руб)", callback_data="buy_50")],
        [InlineKeyboardButton(text="100 ⭐ (130 руб)", callback_data="buy_100")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    ])

def accounts_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Индонезия", callback_data="country_indonesia")],
        [InlineKeyboardButton(text="Индия", callback_data="country_india")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    ])

def gifts_kb(gifts):
    buttons = []
    for i, g in enumerate(gifts[:10]):
        buttons.append([
            InlineKeyboardButton(
                text=f"🎁 {g.get('name','Подарок')}",
                callback_data=f"gift_{i}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def gift_detail_kb(i):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 15⭐", callback_data=f"pay_{i}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="gifts_menu")]
    ])

# ===== API ПОДАРКОВ =====
async def get_gifts():
    url = f"https://api.telegram.org/bot{API_TOKEN}/getStarGiftOptions"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data.get("ok"):
                return data["result"]
    return []

# ===== СТАРТ =====
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        f"Здравствуйте, {message.from_user.first_name}!",
        reply_markup=main_menu(message.from_user.id)
    )

# ===== МЕНЮ =====
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
    await callback.message.edit_text(
        "Курс: 1⭐ = 1.3 руб\n\nВыберите:",
        reply_markup=stars_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy(callback: CallbackQuery):
    stars = callback.data.split("_")[1]

    prices = {"50": 65, "100": 130}
    price = prices.get(stars, 0)

    save_order(callback.from_user.id, "stars", f"{stars} stars", "rub")

    await callback.message.edit_text(
        f"⭐ Покупка {stars} звезд\n\n"
        f"💰 Цена: {price} руб\n\n"
        f"📩 Напишите продавцу: @{SELLER_USERNAME}"
    )

    await callback.answer()

# ===== АККАУНТЫ =====
@dp.callback_query(F.data == "accounts_menu")
async def accounts(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите страну:",
        reply_markup=accounts_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("country_"))
async def country(callback: CallbackQuery):
    country = callback.data.split("_")[1]
    name = "Индонезия" if country == "indonesia" else "Индия"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить (40 руб)", callback_data=f"buy_acc_{country}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="accounts_menu")]
    ])

    await callback.message.edit_text(f"{name}\n\nЦена: 40 руб", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_acc_"))
async def buy_account(callback: CallbackQuery):
    country = callback.data.split("_")[2]
    name = "Индонезия" if country == "indonesia" else "Индия"

    save_order(callback.from_user.id, "account", name, "rub")

    await callback.message.edit_text(
        f"✅ Заказ оформлен!\n\n"
        f"🌍 Аккаунт: {name}\n"
        f"💰 Цена: 40 руб\n\n"
        f"📩 Напишите продавцу: @{SELLER_USERNAME}"
    )
    await callback.answer()

# ===== ПОДАРКИ =====
@dp.callback_query(F.data == "gifts_menu")
async def gifts(callback: CallbackQuery):
    await callback.message.edit_text("Загрузка подарков...")
    gifts = await get_gifts()

    if not gifts:
        await callback.message.edit_text("Ошибка загрузки")
        return

    dp["gifts"] = gifts

    text = "🎁 <b>Доступные подарки</b>\n\n"
    for g in gifts[:10]:
        text += f"{g.get('name')} — {g.get('star_count')}⭐\n"

    await callback.message.edit_text(text, reply_markup=gifts_kb(gifts))
    await callback.answer()

# ===== ДЕТАЛИ ПОДАРКА =====
@dp.callback_query(F.data.startswith("gift_"))
async def gift_detail(callback: CallbackQuery):
    gifts = dp.get("gifts", [])
    i = int(callback.data.split("_")[1])

    gift = gifts[i]
    name = gift.get("name", "Подарок")
    animation_url = gift.get("animation_url")

    text = f"🎁 <b>{name}</b>\n\n⏱ 7 дней\n💰 15⭐"

    await callback.message.delete()

    if animation_url:
        await callback.message.answer_animation(
            animation=animation_url,
            caption=text,
            reply_markup=gift_detail_kb(i)
        )
    else:
        await callback.message.answer(text, reply_markup=gift_detail_kb(i))

    await callback.answer()

# ===== ОПЛАТА =====
@dp.callback_query(F.data.startswith("pay_"))
async def pay(callback: CallbackQuery):
    i = int(callback.data.split("_")[1])

    prices = [LabeledPrice(label="Аренда подарка", amount=15)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Аренда подарка",
        description="7 дней",
        payload=f"gift_{i}",
        currency="XTR",
        prices=prices,
        provider_token=""
    )
    await callback.answer()

# ===== ПРЕДЧЕК =====
@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

# ===== УСПЕШНАЯ ОПЛАТА =====
@dp.message(F.successful_payment)
async def success(message: Message):
    payload = message.successful_payment.invoice_payload

    if payload.startswith("gift_"):
        gifts = dp.get("gifts", [])
        i = int(payload.split("_")[1])

        name = gifts[i].get("name", "Подарок")

        save_order(message.from_user.id, "gift", name, "stars")

        await message.answer(
            f"✅ Оплачено!\n\n🎁 {name}\n⏱ 7 дней доступа"
        )

# ===== АДМИН =====
@dp.callback_query(F.data == "admin_panel")
async def admin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return

    cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10")
    orders = cursor.fetchall()

    if not orders:
        text = "📭 Заказов нет"
    else:
        text = "📦 Последние заказы:\n\n"
        for o in orders:
            text += f"#{o[0]} | {o[2]} | {o[3]} | {o[5]}\n"

    await callback.message.edit_text(text)
    await callback.answer()

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
