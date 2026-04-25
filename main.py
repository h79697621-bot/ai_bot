import asyncio
import logging
import sqlite3
import os
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
                  (user_id, item_type, item_name, payment_method, "pending", str(datetime.now())))
    conn.commit()

def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Фото для приветствия", callback_data="admin_set_welcome_photo")],
        [InlineKeyboardButton(text="Фото для звезд", callback_data="admin_set_stars_photo")],
        [InlineKeyboardButton(text="Фото для аккаунтов", callback_data="admin_set_accounts_photo")],
        [InlineKeyboardButton(text="Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
    ])

async def send_with_photo(chat_id, text, photo_key, reply_markup=None):
    photo_path = get_setting(photo_key)
    
    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=text,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            log.error(f"Ошибка отправки фото: {e}")
            return False
    return False

async def edit_with_photo(message, text, photo_key, reply_markup=None):
    photo_path = get_setting(photo_key)
    
    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            await message.delete()
            await message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            log.error(f"Ошибка отправки фото: {e}")
            return False
    return False

def main_menu_kb(user_id):
    admin_status = is_admin(user_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить звезды", callback_data="stars_menu")],
        [InlineKeyboardButton(text="Аккаунты", callback_data="accounts_menu")]
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

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    text = f"Здравствуйте, {username}!\n\nДобро пожаловать в магазин!\n\nВыберите раздел:"
    
    photo_sent = await send_with_photo(
        chat_id=user_id,
        text=text,
        photo_key="welcome_photo",
        reply_markup=main_menu_kb(user_id)
    )
    
    if not photo_sent:
        await message.answer(text, reply_markup=main_menu_kb(user_id))

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    text = f"Здравствуйте, {callback.from_user.first_name}!\n\nВыберите раздел:"
    
    await edit_with_photo(
        message=callback.message,
        text=text,
        photo_key="welcome_photo",
        reply_markup=main_menu_kb(user_id)
    )
    await callback.answer()

@dp.callback_query(F.data == "stars_menu")
async def stars_menu(callback: CallbackQuery):
    text = "Курс: 1 звезда = 1.3 руб\n\nВыберите количество:"
    
    await edit_with_photo(
        message=callback.message,
        text=text,
        photo_key="stars_photo",
        reply_markup=stars_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_stars(callback: CallbackQuery):
    stars = callback.data.split("_")[1]
    price = {"50": 65, "100": 130, "200": 260, "300": 390, "400": 520, "500": 650}[stars]
    text = f"Покупка {stars} звезд\n\nЦена: {price} руб\n\nПо вопросам оплаты: @{SELLER_USERNAME}"
    
    await edit_with_photo(
        message=callback.message,
        text=text,
        photo_key="stars_photo",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
            [InlineKeyboardButton(text="Назад", callback_data="stars_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "accounts_menu")
async def accounts_menu(callback: CallbackQuery):
    text = "Выберите страну:"
    
    await edit_with_photo(
        message=callback.message,
        text=text,
        photo_key="accounts_photo",
        reply_markup=accounts_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("country_"))
async def choose_country(callback: CallbackQuery):
    country = callback.data.split("_")[1]
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    text = f"{country_name}\n\nЦена: 30 звезд или 40 руб\n\nВыберите способ оплаты:"
    
    await edit_with_photo(
        message=callback.message,
        text=text,
        photo_key="accounts_photo",
        reply_markup=buy_account_kb(country)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_stars_account_"))
async def pay_account_stars(callback: CallbackQuery):
    country = callback.data.replace("pay_stars_account_", "")
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    text = f"Оплата аккаунта {country_name}\n\nЦена: 30 звезд\n\nПо вопросам оплаты: @{SELLER_USERNAME}"
    
    save_order(callback.from_user.id, "account", country_name, "stars")
    
    await edit_with_photo(
        message=callback.message,
        text=text,
        photo_key="stars_photo",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
            [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_rub_account_"))
async def pay_account_rub(callback: CallbackQuery):
    country = callback.data.replace("pay_rub_account_", "")
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    text = f"Оплата аккаунта {country_name}\n\nЦена: 40 руб\n\nСвяжитесь с продавцом: @{SELLER_USERNAME}"
    
    save_order(callback.from_user.id, "account", country_name, "rub")
    
    await edit_with_photo(
        message=callback.message,
        text=text,
        photo_key="accounts_photo",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Написать продавцу", url=f"https://t.me/{SELLER_USERNAME}")],
            [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
        ])
    )
    await callback.answer()

# ========== АДМИН ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.edit_text("Админ-панель", reply_markup=admin_panel_kb())
    await callback.answer()

@dp.callback_query(F.data == "admin_set_welcome_photo")
async def admin_set_welcome_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Отправьте фото для приветствия")
    await callback.answer()

@dp.callback_query(F.data == "admin_set_stars_photo")
async def admin_set_stars_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Отправьте фото для раздела Звезды")
    await callback.answer()

@dp.callback_query(F.data == "admin_set_accounts_photo")
async def admin_set_accounts_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Отправьте фото для раздела Аккаунты")
    await callback.answer()

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    cursor.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 20')
    orders = cursor.fetchall()
    if not orders:
        await callback.message.answer("Нет заказов")
    else:
        text = "Последние заказы:\n\n"
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
    timestamp = int(datetime.now().timestamp())
    file_path = os.path.join(PHOTO_DIR, f"{timestamp}.jpg")
    await bot.download_file(file.file_path, file_path)
    
    caption = message.caption.lower() if message.caption else ""
    
    if "привет" in caption or "welcome" in caption:
        set_setting("welcome_photo", file_path)
        await message.answer("Фото для приветствия сохранено!")
    elif "звезд" in caption or "stars" in caption:
        set_setting("stars_photo", file_path)
        await message.answer("Фото для раздела Звезды сохранено!")
    elif "аккаунт" in caption or "account" in caption:
        set_setting("accounts_photo", file_path)
        await message.answer("Фото для раздела Аккаунты сохранено!")
    else:
        set_setting("welcome_photo", file_path)
        await message.answer("Фото сохранено как приветствие")

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа")
        return
    await message.answer("Админ-панель", reply_markup=admin_panel_kb())

async def main():
    try:
        log.info("Запуск бота...")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        log.info("Бот остановлен")

if __name__ == '__main__':
    asyncio.run(main())
