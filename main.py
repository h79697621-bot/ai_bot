import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, LabeledPrice, PreCheckoutQuery
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

async def send_message_safe(message, text, photo_key, reply_markup):
    """Безопасная отправка сообщения - удаляем только если есть что удалять"""
    photo_path = get_setting(photo_key)
    
    try:
        if message.photo or message.text:
            await message.delete()
    except:
        pass
    
    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=reply_markup
            )
        except Exception as e:
            log.error(f"Ошибка фото: {e}")
            await message.answer(text, reply_markup=reply_markup)
    else:
        await message.answer(text, reply_markup=reply_markup)

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
        [InlineKeyboardButton(text="50⭐ (65₽)", callback_data="buy_50")],
        [InlineKeyboardButton(text="100⭐ (130₽)", callback_data="buy_100")],
        [InlineKeyboardButton(text="200⭐ (260₽)", callback_data="buy_200")],
        [InlineKeyboardButton(text="300⭐ (390₽)", callback_data="buy_300")],
        [InlineKeyboardButton(text="400⭐ (520₽)", callback_data="buy_400")],
        [InlineKeyboardButton(text="500⭐ (650₽)", callback_data="buy_500")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_menu")]
    ])

def accounts_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Индонезия", callback_data="country_indonesia")],
        [InlineKeyboardButton(text="Индия", callback_data="country_india")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_menu")]
    ])

def buy_account_kb(country):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Оплатить 30 звезд", callback_data=f"pay_stars_{country}")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="accounts_menu")]
    ])

def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Фото для приветствия", callback_data="admin_set_welcome_photo")],
        [InlineKeyboardButton(text="Фото для звезд", callback_data="admin_set_stars_photo")],
        [InlineKeyboardButton(text="Фото для аккаунтов", callback_data="admin_set_accounts_photo")],
        [InlineKeyboardButton(text="Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_menu")]
    ])

@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    text = f"Здравствуйте, {username}!\n\nДобро пожаловать в магазин!"
    
    await send_message_safe(
        message=message,
        text=text,
        photo_key="welcome_photo",
        reply_markup=main_menu_kb(user_id)
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    text = f"Здравствуйте, {callback.from_user.first_name}!\n\nВыберите раздел:"
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="welcome_photo",
        reply_markup=main_menu_kb(user_id)
    )
    await callback.answer()

@dp.callback_query(F.data == "stars_menu")
async def stars_menu(callback: CallbackQuery):
    text = "Курс: 1⭐ = 1.3₽\n\nВыберите количество:"
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="stars_photo",
        reply_markup=stars_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_stars(callback: CallbackQuery):
    stars = callback.data.split("_")[1]
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer_invoice(
        title=f"{stars} звезд",
        description=f"Покупка {stars} звезд",
        payload=f"stars_{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{stars} звезд", amount=int(stars))],
        start_parameter=f"buy_stars_{stars}"
    )
    await callback.answer()

@dp.callback_query(F.data == "accounts_menu")
async def accounts_menu(callback: CallbackQuery):
    text = "Выберите страну:"
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="accounts_photo",
        reply_markup=accounts_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("country_"))
async def choose_country(callback: CallbackQuery):
    country = callback.data.split("_")[1]
    country_name = "🇮🇩 Индонезия" if country == "indonesia" else "🇮🇳 Индия"
    text = f"{country_name}\n\nЦена: 30⭐\n\nНажмите на кнопку для оплаты:"
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="accounts_photo",
        reply_markup=buy_account_kb(country)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_stars_"))
async def pay_account_stars(callback: CallbackQuery):
    country = callback.data.replace("pay_stars_", "")
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer_invoice(
        title=f"Аккаунт {country_name}",
        description=f"Покупка аккаунта {country_name}",
        payload=f"account_{country}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Аккаунт {country_name}", amount=30)],
        start_parameter=f"buy_account_{country}"
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id
    payment = message.successful_payment
    payload = payment.invoice_payload
    stars = payment.total_amount
    
    if payload.startswith("stars_"):
        await message.answer(
            f"✅ Оплачено {stars} звезд!\n\nСпасибо за покупку!",
            reply_markup=main_menu_kb(user_id)
        )
    
    elif payload.startswith("account_"):
        country = payload.replace("account_", "")
        country_name = "Индонезия" if country == "indonesia" else "Индия"
        
        save_order(user_id, "account", country_name, "stars")
        
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                f"🆕 Новый заказ!\n\n"
                f"Пользователь: {message.from_user.first_name}\n"
                f"ID: {user_id}\n"
                f"Товар: Аккаунт {country_name}\n"
                f"Оплата: {stars} звезд"
            )
        
        await message.answer(
            f"✅ Оплата прошла успешно!\n\n"
            f"Аккаунт {country_name} будет отправлен в течение 5 минут.\n"
            f"Спасибо за покупку!",
            reply_markup=main_menu_kb(user_id)
        )

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    await send_message_safe(
        message=callback.message,
        text="👑 Админ-панель",
        photo_key="welcome_photo",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_set_welcome_photo")
async def admin_set_welcome_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("📸 Отправьте фото (подпись: привет)")
    await callback.answer()

@dp.callback_query(F.data == "admin_set_stars_photo")
async def admin_set_stars_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("📸 Отправьте фото (подпись: звезды)")
    await callback.answer()

@dp.callback_query(F.data == "admin_set_accounts_photo")
async def admin_set_accounts_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("📸 Отправьте фото (подпись: аккаунты)")
    await callback.answer()

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    cursor.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 20')
    orders = cursor.fetchall()
    
    if not orders:
        text = "📋 Нет заказов"
    else:
        text = "📋 Заказы:\n\n"
        for order in orders:
            text += f"#{order[0]} | {order[2]} | {order[3]}\n"
    
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
    
    if "привет" in caption:
        set_setting("welcome_photo", file_path)
        await message.answer("✅ Фото для приветствия сохранено!")
    elif "звезды" in caption:
        set_setting("stars_photo", file_path)
        await message.answer("✅ Фото для звезд сохранено!")
    elif "аккаунты" in caption:
        set_setting("accounts_photo", file_path)
        await message.answer("✅ Фото для аккаунтов сохранено!")
    else:
        await message.answer("❌ Укажите подпись: привет, звезды или аккаунты")

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа")
        return
    
    await send_message_safe(
        message=message,
        text="👑 Админ-панель",
        photo_key="welcome_photo",
        reply_markup=admin_panel_kb()
    )

async def main():
    try:
        log.info("Запуск бота...")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        log.info("Бот остановлен")

if __name__ == '__main__':
    asyncio.run(main())
