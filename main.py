import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, PreCheckoutQuery
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

API_TOKEN = '8614544546:AAEiDB080jmjjYQPRsongRt2UcelwUw7heg'

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

router = Router()

conn = sqlite3.connect('shop_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance_stars INTEGER DEFAULT 0
    )
''')

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
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )
''')

conn.commit()

ADMIN_IDS = [8364328997]

def get_user(user_id, username=""):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute('INSERT INTO users (user_id, username, balance_stars) VALUES (?, ?, ?)', 
                      (user_id, username, 0))
        conn.commit()
        return (user_id, username, 0)
    return user

def add_stars(user_id, amount):
    cursor.execute('UPDATE users SET balance_stars = balance_stars + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()

def remove_stars(user_id, amount):
    cursor.execute('UPDATE users SET balance_stars = balance_stars - ? WHERE user_id = ?', (amount, user_id))
    conn.commit()

def get_user_stars(user_id):
    cursor.execute('SELECT balance_stars FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

def set_setting(key, value):
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()

def get_setting(key):
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    return result[0] if result else None

def save_order(user_id, item_type, item_name, payment_method):
    cursor.execute('INSERT INTO orders (user_id, item_type, item_name, payment_method, created_at) VALUES (?, ?, ?, ?, ?)',
                  (user_id, item_type, item_name, payment_method, datetime.now().isoformat()))
    conn.commit()

STARS_PRICES = {50: 50, 100: 100, 200: 200, 300: 300, 400: 400, 500: 500}

def main_menu(user_id):
    stars = get_user_stars(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Баланс: {stars} звезд", callback_data="balance")],
        [InlineKeyboardButton(text="Купить звезды", callback_data="stars_menu")],
        [InlineKeyboardButton(text="Аккаунты", callback_data="accounts_menu")]
    ])

def stars_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 звезд", callback_data="buy_50"), InlineKeyboardButton(text="100 звезд", callback_data="buy_100")],
        [InlineKeyboardButton(text="200 звезд", callback_data="buy_200"), InlineKeyboardButton(text="300 звезд", callback_data="buy_300")],
        [InlineKeyboardButton(text="400 звезд", callback_data="buy_400"), InlineKeyboardButton(text="500 звезд", callback_data="buy_500")],
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
        [InlineKeyboardButton(text="Купить звездами (30 звезд)", callback_data=f"buy_stars_account_{country}")],
        [InlineKeyboardButton(text="Купить переводом (40 руб)", callback_data=f"buy_transfer_account_{country}")],
        [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
    ])

def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Реквизиты перевода", callback_data="admin_set_payment")],
        [InlineKeyboardButton(text="Выдать звезды", callback_data="admin_add_stars")],
        [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Главное меню", callback_data="back_to_menu")]
    ])

@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    get_user(user_id, username)
    await message.answer(
        f"Здравствуйте, {username}!",
        reply_markup=main_menu(user_id)
    )

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Нет доступа")
        return
    await message.answer("Админ-панель", reply_markup=admin_panel_kb())

@dp.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    stars = get_user_stars(user_id)
    await callback.message.answer(f"Ваш баланс: {stars} звезд", reply_markup=main_menu(user_id))
    await callback.answer()

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
        "Выберите количество звезд:",
        reply_markup=stars_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_") and ~F.data.startswith("buy_stars_account_"))
async def buy_stars(callback: CallbackQuery):
    stars = int(callback.data.split("_")[1])
    price = STARS_PRICES[stars]
    
    await callback.message.answer_invoice(
        title=f"{stars} звезд",
        description=f"Покупка {stars} звезд для вашего аккаунта",
        payload=f"stars_{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{stars} звезд", amount=stars)],
        start_parameter=f"buy_{stars}"
    )
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    user_id = message.from_user.id
    payment = message.successful_payment
    stars_amount = payment.total_amount
    invoice_payload = payment.invoice_payload
    
    add_stars(user_id, stars_amount)
    
    await message.answer(
        f"Оплата {stars_amount} звезд успешно получена!\n"
        f"Ваш баланс: {get_user_stars(user_id)} звезд",
        reply_markup=main_menu(user_id)
    )

@dp.callback_query(F.data == "accounts_menu")
async def accounts_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "Каталог аккаунтов\n\nВыберите страну:",
        reply_markup=accounts_menu_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("country_"))
async def choose_country(callback: CallbackQuery):
    country = callback.data.split("_")[1]
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    await callback.message.edit_text(
        f"{country_name}\n\n"
        f"Цена: 30 звезд\n"
        f"Цена переводом: 40 руб\n\n"
        f"Выберите способ оплаты:",
        reply_markup=buy_account_kb(country)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_stars_account_"))
async def buy_account_stars(callback: CallbackQuery):
    country = callback.data.replace("buy_stars_account_", "")
    user_id = callback.from_user.id
    stars = get_user_stars(user_id)
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    if stars >= 30:
        remove_stars(user_id, 30)
        save_order(user_id, "account", country_name, "stars")
        
        await callback.message.edit_text(
            f"Покупка аккаунта {country_name}\n\n"
            f"Оплачено: 30 звезд\n"
            f"Ваш баланс: {get_user_stars(user_id)} звезд",
            reply_markup=back_kb()
        )
    else:
        await callback.message.edit_text(
            f"Недостаточно звезд!\n\n"
            f"Нужно: 30 звезд\n"
            f"У вас: {stars} звезд\n\n"
            f"Пополните баланс в разделе Купить звезды",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Купить звезды", callback_data="stars_menu")],
                [InlineKeyboardButton(text="Назад", callback_data="accounts_menu")]
            ])
        )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_transfer_account_"))
async def buy_account_transfer(callback: CallbackQuery):
    country = callback.data.replace("buy_transfer_account_", "")
    user_id = callback.from_user.id
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    save_order(user_id, "account", country_name, "transfer")
    payment_info = get_setting("payment_info") or "Реквизиты не настроены"
    
    await callback.message.edit_text(
        f"Заказ аккаунта {country_name}\n\n"
        f"К оплате: 40 руб\n\n"
        f"Реквизиты для перевода:\n{payment_info}\n\n"
        f"После оплаты отправьте чек в поддержку",
        reply_markup=back_kb()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа")
        return
    await callback.message.edit_text("Админ-панель", reply_markup=admin_panel_kb())
    await callback.answer()

@dp.callback_query(F.data == "admin_set_payment")
async def admin_set_payment(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Отправьте текст с реквизитами для перевода")
    await callback.answer()

@dp.message(F.text)
async def save_payment_info(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    if len(message.text) > 10:
        set_setting("payment_info", message.text)
        await message.answer("Реквизиты сохранены!")

@dp.callback_query(F.data == "admin_add_stars")
async def admin_add_stars(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Введите: /addstars user_id количество")
    await callback.answer()

@dp.message(Command("addstars"))
async def add_stars_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("/addstars 123456789 100")
        return
    try:
        user_id = int(args[1])
        amount = int(args[2])
        add_stars(user_id, amount)
        await message.answer(f"Выдано {amount} звезд пользователю {user_id}")
    except:
        await message.answer("Ошибка")

async def main():
    dp.include_router(router)
    try:
        log.info("Запуск бота...")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        log.info("Бот остановлен")

if __name__ == '__main__':
    asyncio.run(main())
