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

API_TOKEN = '8799124007:AAGus3HI7KaBbLNPxdB_TA99KYjtQmiNaws'

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
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        language TEXT DEFAULT 'ru'
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_type TEXT,
        item_name TEXT,
        payment_method TEXT,
        amount INTEGER,
        status TEXT,
        created_at TEXT
    )
''')
conn.commit()

ADMIN_IDS = [8364328997, 8318310777]
SELLER_USERNAME = "vorrxy"
PREMIUM_EMOJI_ID = "5348370156340933254"
PHONE_NUMBER = "+79155613790"
BANK_NAME = "Sberbank"
PAYMENT_LINK = "https://www.sberbank.ru/ru/choise_bank?requisiteNumber=79155613790&bankCode=100000000111"
REVIEWS_LINK = "https://t.me/grettpo"

# ID подарков из API
GIFTS = {
    "heart": {"id": "5170145012310081615", "name": "💝 Сердце", "price": 15},
    "bear": {"id": "5170233102089322756", "name": "🧸 Мишка", "price": 15},
    "gift_box": {"id": "5170250947678437525", "name": "🎁 Подарок", "price": 25},
    "rose": {"id": "5168103777563050263", "name": "🌹 Роза", "price": 25},
    "cake": {"id": "5170144170496491616", "name": "🎂 Торт", "price": 50},
    "bouquet": {"id": "5170314324215857265", "name": "💐 Букет", "price": 50},
    "rocket": {"id": "5170564780938756245", "name": "🚀 Ракета", "price": 50},
    "champagne": {"id": "6028601630662853006", "name": "🍾 Шампанское", "price": 50},
    "cup": {"id": "5168043875654172773", "name": "🏆 Кубок", "price": 100},
    "ring": {"id": "5170690322832818290", "name": "💍 Кольцо", "price": 100},
    "diamond": {"id": "5170521118301225164", "name": "💎 Бриллиант", "price": 100},
}

def set_setting(key, value):
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()

def get_setting(key):
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    return result[0] if result else None

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_language(user_id):
    cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute('INSERT INTO users (user_id, language) VALUES (?, ?)', (user_id, "ru"))
        conn.commit()
        return "ru"

def set_language(user_id, lang):
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()

def save_order(user_id, item_type, item_name, payment_method, amount):
    cursor.execute('INSERT INTO orders (user_id, item_type, item_name, payment_method, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (user_id, item_type, item_name, payment_method, amount, "pending", str(datetime.now())))
    conn.commit()

def get_text(lang, key, **kwargs):
    texts = {
        "ru": {
            "welcome": "Здравствуйте, {username}!\n\nВыберите действие:",
            "stars_menu": "Выберите количество:",
            "accounts_menu": "Выберите страну:",
            "choose_payment": "Выберите способ оплаты:",
            "buy_stars_title": "💳 Счет на оплату\n\nТовар: {stars} звезд\nСумма к оплате: {price}₽\n\n🔗 Ссылка для оплаты:\n{link}",
            "buy_account_stars_title": "Аккаунт {country}",
            "buy_account_stars_desc": "Покупка аккаунта {country}",
            "buy_account_rub_title": "💳 Счет на оплату\n\nТовар: Аккаунт {country}\nСумма к оплате: {amount}₽\n\n🔗 Ссылка для оплаты:\n{link}",
            "payment_success": "✅ Оплата прошла успешно!\n\nАккаунт {country} будет отправлен в течение 5 минут.\nСпасибо за покупку!",
            "info_text": "ℹ️ Информация о магазине\n\n📦 Мы продаем аккаунты и звёзды Telegram\n\n💳 После оплаты пришлите скриншот чека в личные сообщения.",
            "lang_changed": "🌐 Язык изменен на русский",
            "lang_changed_en": "🌐 Language changed to English",
            "buy_stars": "Купить звезды",
            "accounts": "Аккаунты",
            "info": "Информация",
            "reviews": "📢 Отзывы",
            "write_seller": "📩 Написать продавцу",
            "admin_panel": "Админ панель",
            "gifts": "🎁 Подарки",
            "select_gift": "🎁 Выберите подарок:",
            "enter_comment": "📝 Введите комментарий к подарку (до 128 символов):",
            "gift_sent": "✅ Подарок отправлен!\n\n🎁 {gift_name}\n💬 Комментарий: {comment}\n💸 Списано звезд: {price}⭐",
            "gift_error": "❌ Ошибка при отправке подарка",
            "back": "◀ Главное меню",
            "back_btn": "◀ Назад",
            "indonesia": "Индонезия",
            "india": "Индия",
            "pay_stars": "⭐ Оплатить звездами",
            "pay_rub": "💳 Оплатить рублями",
            "choose_lang": "🌐 Выберите язык:",
        },
        "en": {
            "welcome": "Hello, {username}!\n\nChoose an action:",
            "stars_menu": "Select quantity:",
            "accounts_menu": "Select country:",
            "choose_payment": "Select payment method:",
            "buy_stars_title": "💳 Payment invoice\n\nProduct: {stars} stars\nAmount to pay: {price}₽\n\n🔗 Payment link:\n{link}",
            "buy_account_stars_title": "Account {country}",
            "buy_account_stars_desc": "Purchase of account {country}",
            "buy_account_rub_title": "💳 Payment invoice\n\nProduct: Account {country}\nAmount to pay: {amount}₽\n\n🔗 Payment link:\n{link}",
            "payment_success": "✅ Payment successful!\n\nAccount {country} will be sent within 5 minutes.\nThank you for your purchase!",
            "info_text": "ℹ️ Store Information\n\n📦 We sell accounts and Telegram stars\n\n💳 After payment, send a screenshot of the receipt in a personal message.",
            "lang_changed": "🌐 Language changed to English",
            "lang_changed_ru": "🌐 Язык изменен на русский",
            "buy_stars": "Buy stars",
            "accounts": "Accounts",
            "info": "Info",
            "reviews": "📢 Reviews",
            "write_seller": "📩 Contact seller",
            "admin_panel": "Admin panel",
            "gifts": "🎁 Gifts",
            "select_gift": "🎁 Select a gift:",
            "enter_comment": "📝 Enter comment for the gift (max 128 characters):",
            "gift_sent": "✅ Gift sent!\n\n🎁 {gift_name}\n💬 Comment: {comment}\n💸 Stars spent: {price}⭐",
            "gift_error": "❌ Error sending gift",
            "back": "◀ Main menu",
            "back_btn": "◀ Back",
            "indonesia": "Indonesia",
            "india": "India",
            "pay_stars": "⭐ Pay with stars",
            "pay_rub": "💳 Pay in rubles",
            "choose_lang": "🌐 Choose language:",
        }
    }
    
    text = texts[lang].get(key, texts["ru"].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text

async def send_message_safe(message, text, photo_key, reply_markup):
    photo_path = get_setting(photo_key)
    
    try:
        if message.photo or message.text:
            await message.delete()
    except:
        pass
    
    final_text = f'<tg-emoji emoji-id="{PREMIUM_EMOJI_ID}"></tg-emoji> {text}'
    
    if photo_path and os.path.exists(photo_path):
        try:
            photo = FSInputFile(photo_path)
            await message.answer_photo(
                photo=photo,
                caption=final_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            log.error(f"Ошибка фото: {e}")
            await message.answer(final_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await message.answer(final_text, reply_markup=reply_markup, parse_mode="HTML")

def main_menu_kb(user_id):
    lang = get_language(user_id)
    admin_status = is_admin(user_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "buy_stars"), callback_data="stars_menu")],
        [InlineKeyboardButton(text=get_text(lang, "accounts"), callback_data="accounts_menu")],
        [InlineKeyboardButton(text=get_text(lang, "info"), callback_data="info_menu")]
    ])
    if admin_status:
        kb.inline_keyboard.append([InlineKeyboardButton(text=get_text(lang, "admin_panel"), callback_data="admin_panel")])
    return kb

def stars_menu_kb(user_id):
    lang = get_language(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50⭐", callback_data="buy_50")],
        [InlineKeyboardButton(text="100⭐", callback_data="buy_100")],
        [InlineKeyboardButton(text="200⭐", callback_data="buy_200")],
        [InlineKeyboardButton(text="300⭐", callback_data="buy_300")],
        [InlineKeyboardButton(text="400⭐", callback_data="buy_400")],
        [InlineKeyboardButton(text="500⭐", callback_data="buy_500")],
        [InlineKeyboardButton(text=get_text(lang, "back"), callback_data="back_to_menu")]
    ])

def accounts_menu_kb(user_id):
    lang = get_language(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "indonesia"), callback_data="country_indonesia")],
        [InlineKeyboardButton(text=get_text(lang, "india"), callback_data="country_india")],
        [InlineKeyboardButton(text=get_text(lang, "back"), callback_data="back_to_menu")]
    ])

def buy_account_kb(user_id, country):
    lang = get_language(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "pay_stars"), callback_data=f"pay_stars_{country}")],
        [InlineKeyboardButton(text=get_text(lang, "pay_rub"), callback_data=f"pay_rub_{country}")],
        [InlineKeyboardButton(text=get_text(lang, "back_btn"), callback_data="accounts_menu")]
    ])

def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Фото приветствия", callback_data="admin_set_welcome_photo")],
        [InlineKeyboardButton(text="📸 Фото звезд", callback_data="admin_set_stars_photo")],
        [InlineKeyboardButton(text="📸 Фото аккаунтов", callback_data="admin_set_accounts_photo")],
        [InlineKeyboardButton(text="🎁 Подарки", callback_data="admin_gifts")],
        [InlineKeyboardButton(text="📋 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="◀ Главное меню", callback_data="back_to_menu")]
    ])

def gifts_list_kb():
    buttons = []
    for gift_key, gift_data in GIFTS.items():
        buttons.append([InlineKeyboardButton(text=f"{gift_data['name']} — {gift_data['price']}⭐", callback_data=f"gift_select_{gift_key}")])
    buttons.append([InlineKeyboardButton(text="◀ Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")]
    ])

@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.first_name
    lang = get_language(user_id)
    
    text = get_text(lang, "welcome", username=username)
    
    await send_message_safe(
        message=message,
        text=text,
        photo_key="welcome_photo",
        reply_markup=main_menu_kb(user_id)
    )

@dp.message(Command("lang"))
async def change_lang(message: Message):
    await message.answer("🌐 Выберите язык / Choose language:", reply_markup=lang_kb())

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    set_language(user_id, lang)
    
    if lang == "ru":
        text = get_text("ru", "lang_changed")
    else:
        text = get_text("en", "lang_changed")
    
    await callback.message.answer(text)
    await callback.message.delete()
    await start(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.first_name
    lang = get_language(user_id)
    
    text = get_text(lang, "welcome", username=username)
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="welcome_photo",
        reply_markup=main_menu_kb(user_id)
    )
    await callback.answer()

@dp.callback_query(F.data == "info_menu")
async def info_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_language(user_id)
    
    text = get_text(lang, "info_text")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "write_seller"), url=f"https://t.me/{SELLER_USERNAME}")],
        [InlineKeyboardButton(text=get_text(lang, "reviews"), url=REVIEWS_LINK)],
        [InlineKeyboardButton(text=get_text(lang, "back"), callback_data="back_to_menu")]
    ])
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="welcome_photo",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data == "stars_menu")
async def stars_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_language(user_id)
    
    text = get_text(lang, "stars_menu")
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="stars_photo",
        reply_markup=stars_menu_kb(user_id)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_stars(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_language(user_id)
    stars = callback.data.split("_")[1]
    prices = {"50": 65, "100": 130, "200": 260, "300": 390, "400": 520, "500": 650}
    price = prices.get(stars, 0)
    
    text = get_text(lang, "buy_stars_title", stars=stars, price=price, link=PAYMENT_LINK)
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="stars_photo",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=PAYMENT_LINK)],
            [InlineKeyboardButton(text=get_text(lang, "back_btn"), callback_data="stars_menu")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "accounts_menu")
async def accounts_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_language(user_id)
    
    text = get_text(lang, "accounts_menu")
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="accounts_photo",
        reply_markup=accounts_menu_kb(user_id)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("country_"))
async def choose_country(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_language(user_id)
    country = callback.data.split("_")[1]
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    text = f"{country_name}\n\n{get_text(lang, 'choose_payment')}"
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="accounts_photo",
        reply_markup=buy_account_kb(user_id, country)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_stars_"))
async def pay_account_stars(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_language(user_id)
    country = callback.data.replace("pay_stars_", "")
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    title = get_text(lang, "buy_account_stars_title", country=country_name)
    description = get_text(lang, "buy_account_stars_desc", country=country_name)
    
    await callback.message.answer_invoice(
        title=title,
        description=description,
        payload=f"account_{country}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=30)],
        start_parameter=f"buy_account_{country}"
    )
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_rub_"))
async def pay_account_rub(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_language(user_id)
    country = callback.data.replace("pay_rub_", "")
    country_name = "Индонезия" if country == "indonesia" else "Индия"
    
    amount = 40
    
    text = get_text(lang, "buy_account_rub_title", country=country_name, amount=amount, link=PAYMENT_LINK)
    
    save_order(user_id, "account", country_name, "rub", amount)
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="accounts_photo",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=PAYMENT_LINK)],
            [InlineKeyboardButton(text=get_text(lang, "back_btn"), callback_data="accounts_menu")]
        ])
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    user_id = message.from_user.id
    lang = get_language(user_id)
    payment = message.successful_payment
    payload = payment.invoice_payload
    stars = payment.total_amount
    
    if payload.startswith("account_"):
        country = payload.replace("account_", "")
        country_name = "Индонезия" if country == "indonesia" else "Индия"
        
        save_order(user_id, "account", country_name, "stars", stars)
        
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                f"🆕 Новый заказ!\n\n"
                f"Пользователь: {message.from_user.first_name}\n"
                f"ID: {user_id}\n"
                f"Товар: Аккаунт {country_name}\n"
                f"Оплата: {stars} звезд"
            )
        
        text = get_text(lang, "payment_success", country=country_name)
        
        try:
            await message.delete()
        except:
            pass
        
        await message.answer(text, reply_markup=main_menu_kb(user_id))

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    text = "Админ-панель\n\nВыберите действие:"
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="welcome_photo",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_set_welcome_photo")
async def admin_set_welcome_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Отправьте фото (подпись: привет)")
    await callback.answer()

@dp.callback_query(F.data == "admin_set_stars_photo")
async def admin_set_stars_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Отправьте фото (подпись: звезды)")
    await callback.answer()

@dp.callback_query(F.data == "admin_set_accounts_photo")
async def admin_set_accounts_photo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Отправьте фото (подпись: аккаунты)")
    await callback.answer()

@dp.callback_query(F.data == "admin_gifts")
async def admin_gifts_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    lang = get_language(callback.from_user.id)
    text = get_text(lang, "select_gift")
    
    await send_message_safe(
        message=callback.message,
        text=text,
        photo_key="welcome_photo",
        reply_markup=gifts_list_kb()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("gift_select_"))
async def gift_select(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    gift_key = callback.data.replace("gift_select_", "")
    gift_info = GIFTS.get(gift_key)
    
    if not gift_info:
        await callback.answer("Подарок не найден")
        return
    
    lang = get_language(callback.from_user.id)
    set_setting("selected_gift", gift_key)
    await callback.message.answer(get_text(lang, "enter_comment"))
    await callback.answer()

@dp.message(F.text)
async def send_gift_with_comment(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    gift_key = get_setting("selected_gift")
    if not gift_key:
        return
    
    gift_info = GIFTS.get(gift_key)
    if not gift_info:
        set_setting("selected_gift", "")
        return
    
    comment = message.text.strip()
    if len(comment) > 128:
        await message.answer("❌ Комментарий слишком длинный! Максимум 128 символов.")
        return
    
    lang = get_language(message.from_user.id)
    
    try:
        await bot.send_gift(
            business_connection_id=None,
            user_id=message.from_user.id,
            gift_id=gift_info["id"],
            text=comment,
            text_parse_mode="HTML"
        )
        
        await message.answer(
            get_text(lang, "gift_sent", 
                    gift_name=gift_info["name"], 
                    comment=comment, 
                    price=gift_info["price"])
        )
        
        set_setting("selected_gift", "")
        
    except Exception as e:
        log.error(f"Ошибка отправки подарка: {e}")
        await message.answer(get_text(lang, "gift_error"))

@dp.callback_query(F.data == "admin_orders")
async def admin_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    
    cursor.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 20')
    orders = cursor.fetchall()
    
    if not orders:
        text = "Нет заказов"
    else:
        text = "Заказы:\n\n"
        for order in orders:
            text += f"#{order[0]} | {order[2]} | {order[3]} | {order[4]} {order[5]} | {order[7]}\n"
    
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
        await message.answer("Фото для приветствия сохранено!")
    elif "звезды" in caption:
        set_setting("stars_photo", file_path)
        await message.answer("Фото для звезд сохранено!")
    elif "аккаунты" in caption:
        set_setting("accounts_photo", file_path)
        await message.answer("Фото для аккаунтов сохранено!")
    else:
        await message.answer("Укажите подпись: привет, звезды или аккаунты")

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Нет доступа")
        return
    
    text = "Админ-панель\n\nВыберите действие:"
    
    await send_message_safe(
        message=message,
        text=text,
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
