import asyncio
import logging
import sqlite3
import os
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

API_TOKEN = '8614544546:AAEiDB080jmjjYQPRsongRt2UcelwUw7heg'

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

PHOTO_DIR = "photos"
os.makedirs(PHOTO_DIR, exist_ok=True)

conn = sqlite3.connect('shop_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
''')
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

ADMIN_IDS = [8364328997]
SELLER_USERNAME = "vorrxy"

def set_setting(key, value):
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()

def get_setting(key):
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    return result[0] if result else None

def is_admin(user_id):
    return user_id in ADMIN_IDS

def save_order(user_id, item_type, item_name, payment_method):
    cursor.execute('INSERT INTO orders (user_id, item_type, item_name, payment_method, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                  (user_id, item_type, item_name, payment_method, "pending", str(asyncio.get_event_loop().time())))
    conn.commit()

def main_menu(user_id):
    admin_status = is_admin(user_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить звезды", callback_data="stars_menu")],
        [InlineKeyboardButton(text="Аккаунты", callback_data="accounts_menu")],
        [InlineKeyboardButton(text="Подарки", callback_data="gifts_menu")]
    ])
    if admin_status:
        kb.inline_keyboard.append([InlineKeyboardButton(text="Админ панель", callback_data="admin_panel")])
    return kb

def stars_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 звезд (65 руб)", callback_data="buy_50")],
        [InlineKeyboardButton(text="100 звезд (130 руб)", callback_data="buy_100")],
        [InlineKeyboardButton(text="200 звезд (260 руб)", callback_data="buy_200")],
        [InlineKeyboardButton(text="300 звезд (390 руб)", callback_data="buy_300")],
        [InlineKeyboardButton(text="400 звезд (520 руб)", callback_data="buy_400")],
        [InlineKeyboardButton(text="500 звезд (650 руб)", callback_data="buy_500")],
        [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
    ])

def accounts_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Индонезия", callback_data="country_indonesia")],
        [InlineKeyboardButton(text="Индия", callback_data="country_india")],
        [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
    ])

def buy_account_kb(country):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить звездами (30 звезд)", callback_data=f"pay_stars_account_{country}")],
        [InlineKeyboardButton(text="Купить рублями (40 руб)", callback_data=f"pay_rub_account_{country}")],
        [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
    ])

def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Фото для товара", callback_data="admin_set_photo")],
        [InlineKeyboardButton(text="Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
    ])

# ========== ПОДАРКИ ==========
async def get_gifts_list():
    """Получает список доступных подарков через Telegram API"""
    url = f"https://api.telegram.org/bot{API_TOKEN}/getStarGiftOptions"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                if data.get("ok"):
                    return data.get("result", [])
                else:
                    log.error(f"Ошибка API: {data}")
                    return []
    except Exception as e:
        log.error(f"Ошибка получения подарков: {e}")
        return []

def format_gift_text(gift):
    """Форматирует текст для одного подарка"""
    name = gift.get("name", "Без названия")
    stars = gift.get("star_count", 15)
    supply = gift.get("supply", "?")
    total = gift.get("total_count", supply)
    
    return (f"🎁 {name}\n"
            f"⭐ Цена: {stars} звезд\n"
            f"📦 В наличии: {supply}/{total}\n"
            f"⏱ Аренда на 7 дней\n\n")

def gifts_menu_kb(gifts):
    """Создает клавиатуру со списком подарков"""
    buttons = []
    for i, gift in enumerate(gifts[:10]):  # максимум 10 подарков
        name = gift.get("name", "Подарок")
        buttons.append([InlineKeyboardButton(text=f"🎁 {name}", callback_data=f"gift_{i}")])
    buttons.append([InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def gift_detail_kb(gift_index):
    """Клавиатура для конкретного подарка"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Арендовать на 7 дней (15⭐)", callback_data=f"rent_gift_{gift_index}")],
        [InlineKeyboardButton(text="Назад к списку", callback_data="gifts_menu")]
    ])

@dp.callback_query(F.data == "gifts_menu")
async def gifts_menu(callback: CallbackQuery):
    await callback.message.edit_text("🔄 Загрузка списка подарков...")
    
    gifts = await get_gifts_list()
    
    if not gifts:
        await callback.message.edit_text(
            "❌ Не удалось загрузить список подарков.\nПопробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
            ])
        )
        await callback.answer()
        return
    
    # Сохраняем список подарков в настройки для последующего доступа
    import json
    set_setting("gifts_list", json.dumps(gifts))
    
    text = "🎁 <b>Доступные подарки для аренды</b>\n\n"
    for i, gift in enumerate(gifts[:10]):
        text += format_gift_text(gift)
    text += "\n💰 <b>Условия аренды:</b>\n"
    text += "• Срок аренды: 7 дней\n"
    text += "• Стоимость: 15 звезд\n"
    text += "• После оплаты подарок появится в вашем профиле\n\n"
    text += f"По всем вопросам: @{SELLER_USERNAME}"
    
    await callback.message.edit_text(text, reply_markup=gifts_menu_kb(gifts[:10]))
    await callback.answer()

@dp.callback_query(F.data.startswith("gift_"))
async def gift_detail(callback: CallbackQuery):
    import json
    gift_index = int(callback.data.split("_")[1])
    
    gifts_json = get_setting("gifts_list")
    if not gifts_json:
        await callback.answer("Ошибка: список подарков не загружен")
        return
    
    gifts = json.loads(gifts_json)
    if gift_index >= len(gifts):
        await callback.answer("Подарок не найден")
        return
    
    gift = gifts[gift_index]
    name = gift.get("name", "Без названия")
    stars = gift.get("star_count", 15)
    supply = gift.get("supply", "?")
    total = gift.get("total_count", supply)
    
    # Получаем анимацию подарка (если есть)
    animation_url = gift.get("animation_url", "")
    sticker = gift.get("sticker", {})
    file_id = sticker.get("file_id") if sticker else None
    
    text = (f"🎁 <b>{name}</b>\n\n"
            f"⭐ Цена: {stars} звезд\n"
            f"📦 Доступно: {supply}/{total}\n"
            f"⏱ Аренда: 7 дней\n\n"
            f"После аренды подарок появится в вашем профиле на 7 дней.\n\n"
            f"По вопросам: @{SELLER_USERNAME}")
    
    if file_id:
        try:
            await callback.message.delete()
            await callback.message.answer_animation(
                animation=file_id,
                caption=text,
                reply_markup=gift_detail_kb(gift_index)
            )
        except Exception as e:
            log.error(f"Ошибка отправки анимации: {e}")
            await callback.message.edit_text(text, reply_markup=gift_detail_kb(gift_index))
    elif animation_url:
        await callback.message.edit_text(text, reply_markup=gift_detail_kb(gift_index))
    else:
        await callback.message.edit_text(text, reply_markup=gift_detail_kb(gift_index))
    
    await callback.answer()

@dp.callback_query(F.data.startswith("rent_gift_"))
async def rent_gift(callback: CallbackQuery):
    import json
    gift_index = int(callback.data.split("_")[2])
    
    gifts_json = get_setting("gifts_list")
    if not gifts_json:
        await callback.answer("Ошибка: список подарков не загружен")
        return
    
    gifts = json.loads(gifts_json)
    if gift_index >= len(gifts):
        await callback.answer("Подарок не найден")
        return
    
    gift = gifts[gift_index]
    name = gift.get("name", "Без названия")
    
    # Сохраняем заказ
    save_order(callback.from_user.id, "gift_rent", name, "stars")
    
    # Уведомляем админа
    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"🆕 Запрос на аренду подарка!\n\n"
            f👤 Пользователь: {callback.from_user.first_name}\n"
            f🆔 ID: {callback.from_user.id}\n"
            f🎁 Подарок: {name}\n"
            f💰 Стоимость: 15 звезд\n"
            f⏱ Срок: 7 дней"
        )
    
    # Отправляем пользователю сообщение с контактом продавца
    photo_path = get_setting("stars_photo")
    text = (f"✨ <b>Запрос на аренду подарка отправлен!</b>\n\n"
            f"🎁 Подарок: {name}\n"
            f"⭐ Стоимость: 15 звезд\n"
            f"⏱ Срок: 7 дней\n\n"
            f"Свяжитесь с продавцом для оплаты и получения подарка: @{SELLER_USERNAME}")
    
    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
                    [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
                ])
            )
        except:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
                [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
            ]))
    else:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
            [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
        ]))
    
    await callback.answer()

# ========== ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    await message.answer(
        f"Здравствуйте, {username}!",
        reply_markup=main_menu(user_id)
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        f"Здравствуйте, {callback.from_user.first_name}!",
        reply_markup=main_menu(user_id)
    )
    await callback.answer()

@dp.callback_query(F.data == "stars_menu")
async def stars_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Курс: 1 звезда = 1.3 руб\n\nВыберите количество:",
        reply_markup=stars_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_stars(callback: CallbackQuery):
    stars = callback.data.split("_")[1]
    price = {"50": 65, "100": 130, "200": 260, "300": 390, "400": 520, "500": 650}[stars]
    
    photo_path = get_setting("stars_photo")
    text = f"Покупка {stars} звезд\n\nЦена: {price} руб\n\nПо вопросам оплаты: @{SELLER_USERNAME}"
    
    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
                    [InlineKeyboardButton(text="Назад", callback_data="stars_menu")]
                ])
            )
        except:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
                [InlineKeyboardButton(text="Назад", callback_data="stars_menu")]
            ]))
    else:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
            [InlineKeyboardButton(text="Назад", callback_data="stars_menu")]
        ]))
    await callback.answer()

@dp.callback_query(F.data == "accounts_menu")
async def accounts_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите страну:",
        reply_markup=accounts_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("country_"))
async def choose_country(callback: CallbackQuery):
    country = callback.data.split("_")[1]
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    await callback.message.edit_text(
        f"{country_name}\n\nЦена: 30 звезд или 40 руб\n\nВыберите способ оплаты:",
        reply_markup=buy_account_kb(country)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_stars_account_"))
async def pay_account_stars(callback: CallbackQuery):
    country = callback.data.replace("pay_stars_account_", "")
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    photo_path = get_setting("stars_photo")
    text = f"Оплата аккаунта {country_name}\n\nЦена: 30 звезд\n\nПо вопросам оплаты: @{SELLER_USERNAME}"
    
    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
                    [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
                ])
            )
        except:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
                [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
            ]))
    else:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
            [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
        ]))
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_rub_account_"))
async def pay_account_rub(callback: CallbackQuery):
    country = callback.data.replace("pay_rub_account_", "")
    country_name = "Индонезия" если country == "indonesia" else "Индия"
    
    text = f"Оплата аккаунта {country_name}\n\nЦена: 40 руб\n\nСвяжитесь с продавцом для оплаты: @{SELLER_USERNAME}"
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
        [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
    ]))
    await callback.answer()

# ========== АДМИН ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.edit_text("👑 Админ-панель", reply_markup=admin_panel_kb())
    await callback.answer()

@dp.callback_query(F.data == "admin_set_photo")
async def admin_set_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Отправьте фото для товара")
    await callback.answer()

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    cursor.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 20')
    orders = cursor.fetchall()
    if not orders:
        await callback.message.answer("📋 Нет заказов")
    else:
        text = "📋 Последние заказы:\n\n"
        for order in orders:
            text += f"#{order[0]} | {order[2]} | {order[3]} | {order[5]}\n"
        await callback.message.answer(text)
    await callback.answer()

@dp.message(F.photo)
async def save_photo(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа")
        return
    
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    timestamp = int(asyncio.get_event_loop().time())
    file_path = os.path.join(PHOTO_DIR, f"{timestamp}.jpg")
    await bot.download_file(file.file_path, file_path)
    
    set_setting("stars_photo", file_path)
    await message.answer("✅ Фото для товара сохранено!")

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа")
        return
    await message.answer("👑 Админ-панель", reply_markup=admin_panel_kb())

async def main():
    try:
        log.info("Запуск бота...")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        log.info("Бот остановлен")

if __name__ == '__main__':
    asyncio.run(main())
