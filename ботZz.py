import asyncio
import logging
import os
import json
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from telethon import TelegramClient
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# ==================== НАСТРОЙКИ ====================

BOT_TOKEN_SHOP = "8745927128:AAFR4VfgDKVDAkd8qjiLo78mtVjR6nBxp2s"
BOT_TOKEN_USERBOT = "8659247045:AAGZpCA79T4X1WLlrHHj0ZtKKlC4ZTMv_xI"
ADMIN_ID = 8562793772

GIFTS = {
    "1": {"name": "Новый подарок", "id": "5969796561943660080"},
    "2": {"name": "Мишка 8 марта", "id": "5866352046986232958"}
}

# ==================== БОТ №1: МАГАЗИН ====================

shop_bot = Bot(token=BOT_TOKEN_SHOP)
dp_shop = Dispatcher(storage=MemoryStorage())

DB_FILE = "db.json"

def load_db():
    global users, orders, promo_codes
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            users = {int(k): v for k, v in data.get("users", {}).items()}
            orders = data.get("orders", [])
            promo_codes = data.get("promo_codes", {"SALE10": 10, "START20": 20})
            return
        except: pass
    users = {}
    orders = []
    promo_codes = {"SALE10": 10, "START20": 20}

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users, "orders": orders, "promo_codes": promo_codes}, f, ensure_ascii=False, indent=2)

users = {}
orders = []
promo_codes = {}

CATALOG = {
    "bd": {"name": "Бангладеш +880", "stock": 3, "price": 20, "desc": "Свежие номера"},
    "ca": {"name": "Канада +1", "stock": 5, "price": 30, "desc": "Премиум номера"},
    "ru": {"name": "Россия +7", "stock": 10, "price": 50, "desc": "Российские номера"},
}

SHOP_GIFTS = {
    "newgift": {"name": "Новый подарок", "id": "5969796561943660080", "price": 40},
    "bear8march": {"name": "Мишка 8 марта", "id": "5866352046986232958", "price": 40}
}

class ShopStates(StatesGroup):
    promo = State()
    broadcast = State()
    add_stock = State()
    give_balance = State()

def u(id):
    id = int(id)
    if id not in users:
        users[id] = {
            "balance": 0,
            "orders": [],
            "banned": False,
            "reg_date": datetime.now().strftime("%d.%m.%Y"),
            "username": "",
            "used_promos": []
        }
    return users[id]

def is_admin(id): return int(id) == ADMIN_ID
def is_banned(id): return u(id).get("banned", False)

def kb_main(user_id=None):
    rows = [
        [InlineKeyboardButton(text="🛒 Каталог", callback_data="catalog"),
         InlineKeyboardButton(text="🎁 Подарки", callback_data="gift_shop")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
         InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")],
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/ownnadd"),
         InlineKeyboardButton(text="ℹ️ О магазине", callback_data="about")]
    ]
    if user_id and is_admin(user_id):
        rows.append([InlineKeyboardButton(text="⚙️ Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast"),
         InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users")],
        [InlineKeyboardButton(text="📦 Склад", callback_data="adm_stock"),
         InlineKeyboardButton(text="💰 Выдать баланс", callback_data="adm_give")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"),
         InlineKeyboardButton(text="🎫 Промокоды", callback_data="adm_promos")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main")]
    ])

def get_bot_balance():
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN_SHOP}/getStarTransactions", timeout=10)
        total = 0
        for t in r.json().get("result", {}).get("transactions", []):
            total += t.get("amount", 0)
        return total
    except:
        return 0

def send_gift(user_id, gift_id, comment):
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN_SHOP}/sendGift", json={
            "user_id": user_id,
            "gift_id": gift_id,
            "text": comment
        }, timeout=10)
        return r.ok
    except:
        return False

@dp_shop.message(CommandStart())
async def start_shop(m: Message):
    user = u(m.from_user.id)
    user["username"] = m.from_user.username or ""
    save_db()
    if is_banned(m.from_user.id):
        return await m.answer("🚫 Вы заблокированы.")
    
    total_users = len(users)
    await m.answer(
        f"👋 Добро пожаловать, <b>{m.from_user.first_name}</b>!\n\n"
        f"🤖 <b>Магазин</b>\n"
        f"👥 <b>{total_users}</b> пользователей\n\n"
        f"🏪 <b>Магазин</b>\n"
        f"✅ Быстрая выдача\n"
        f"🔒 Безопасная оплата через Stars\n"
        f"💬 Поддержка 24/7\n\n"
        f"Выберите раздел 👇",
        reply_markup=kb_main(m.from_user.id), parse_mode="HTML"
    )
    if is_admin(m.from_user.id):
        await m.answer("⚙️ Вы вошли как <b>Администратор</b>", parse_mode="HTML")

@dp_shop.callback_query(F.data == "main")
async def cb_main(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.answer()
    await c.message.edit_text("🏠 Главное меню", reply_markup=kb_main(c.from_user.id))

@dp_shop.callback_query(F.data == "catalog")
async def cb_catalog(c: CallbackQuery):
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бангладеш 20⭐", callback_data="buy_bd"),
         InlineKeyboardButton(text="Канада 30⭐", callback_data="buy_ca")],
        [InlineKeyboardButton(text="Россия 50⭐", callback_data="buy_ru"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="main")]
    ])
    await c.message.edit_text("🛒 Каталог", reply_markup=kb)

@dp_shop.callback_query(F.data.startswith("buy_"))
async def cb_buy_item(c: CallbackQuery):
    await c.answer()
    k = c.data.split("_")[1]
    v = CATALOG[k]
    user = u(c.from_user.id)
    
    if v['stock'] <= 0:
        return await c.answer("❌ Товар закончился!", show_alert=True)
    
    await shop_bot.send_invoice(c.from_user.id, title=f"Покупка {v['name']}",
        description=f"Оплатите {v['price']} Stars",
        payload=f"acc_{k}_{v['price']}_{v['name']}", 
        currency="XTR", provider_token="",
        prices=[LabeledPrice(label=v['name'], amount=v['price'])])

@dp_shop.callback_query(F.data == "gift_shop")
async def cb_gift_shop(c: CallbackQuery):
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Новый подарок 40⭐", callback_data="buy_gift_newgift")],
        [InlineKeyboardButton(text="Мишка 8 марта 40⭐", callback_data="buy_gift_bear8march")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main")]
    ])
    await c.message.edit_text("🎁 Подарки", reply_markup=kb)

@dp_shop.callback_query(F.data.startswith("buy_gift_"))
async def cb_buy_gift(c: CallbackQuery):
    await c.answer()
    key = c.data.split("_")[2]
    gift = SHOP_GIFTS[key]
    user = u(c.from_user.id)
    
    await shop_bot.send_invoice(c.from_user.id, title=f"Покупка {gift['name']}",
        description=f"Оплатите {gift['price']} Stars",
        payload=f"gift_{gift['id']}_{gift['price']}_{gift['name']}", 
        currency="XTR", provider_token="",
        prices=[LabeledPrice(label=gift['name'], amount=gift['price'])])

@dp_shop.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@dp_shop.message(F.successful_payment)
async def paid(m: Message):
    payload = m.successful_payment.invoice_payload
    amount = m.successful_payment.total_amount
    user = u(m.from_user.id)
    
    if payload.startswith("acc_"):
        parts = payload.split("_")
        k = parts[1]
        price = int(parts[2])
        name = parts[3]
        
        v = CATALOG[k]
        if v['stock'] <= 0:
            await m.answer(f"❌ Товар закончился")
            return
        
        user['balance'] += amount
        user['balance'] -= price
        v['stock'] -= 1
        order = {"id": len(orders)+1, "item": v['name'], "price": price,
                 "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "user_id": m.from_user.id}
        orders.append(order)
        user['orders'].append(order)
        save_db()
        
        await m.answer(
            f"✅ Покупка успешна!\n\n"
            f"🛍 Товар: {v['name']}\n"
            f"💸 Списано: {price}⭐\n"
            f"💰 Остаток: {user['balance']}⭐\n"
            f"🆔 Заказ №{order['id']}\n\n"
            f"📩 Напишите @ownnadd для получения товара",
            reply_markup=kb_main(m.from_user.id)
        )
    
    elif payload.startswith("gift_"):
        parts = payload.split("_")
        gift_id = parts[1]
        price = int(parts[2])
        gift_name = parts[3]
        
        user['balance'] += amount
        user['balance'] -= price
        save_db()
        
        if send_gift(m.from_user.id, gift_id, f"Подарок {gift_name}"):
            await m.answer(
                f"✅ Оплата прошла успешно!\n\n"
                f"🎁 Подарок: {gift_name}\n"
                f"💸 Списано: {price}⭐\n"
                f"💰 Остаток: {user['balance']}⭐\n\n"
                f"🎉 Подарок отправлен вам!",
                reply_markup=kb_main(m.from_user.id)
            )
        else:
            user['balance'] += price
            save_db()
            await m.answer(
                f"❌ Ошибка при отправке подарка!\n\n"
                f"Средства возвращены.\n"
                f"💰 Баланс: {user['balance']}⭐",
                reply_markup=kb_main(m.from_user.id)
            )

@dp_shop.callback_query(F.data == "balance")
async def cb_balance(c: CallbackQuery):
    await c.answer()
    user = u(c.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Пополнить", callback_data="topup")],
        [InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main")]
    ])
    await c.message.edit_text(
        f"💰 Ваш баланс\n\n⭐ Stars: {user['balance']}\n"
        f"📦 Заказов: {len(user['orders'])}\n📅 В боте с: {user['reg_date']}",
        reply_markup=kb
    )

@dp_shop.callback_query(F.data == "topup")
async def cb_topup(c: CallbackQuery):
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 20", callback_data="pay_20"),
         InlineKeyboardButton(text="⭐ 30", callback_data="pay_30")],
        [InlineKeyboardButton(text="⭐ 50", callback_data="pay_50"),
         InlineKeyboardButton(text="⭐ 100", callback_data="pay_100")],
        [InlineKeyboardButton(text="⭐ 200", callback_data="pay_200"),
         InlineKeyboardButton(text="⭐ 500", callback_data="pay_500")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="balance")]
    ])
    await c.message.edit_text("⭐ Пополнение баланса\n\nВыберите сумму:", reply_markup=kb)

@dp_shop.callback_query(F.data.startswith("pay_"))
async def cb_pay(c: CallbackQuery):
    await c.answer()
    amount = int(c.data[4:])
    await shop_bot.send_invoice(c.from_user.id, title=f"Пополнение {amount}⭐",
        description=f"{amount} Stars будут зачислены",
        payload=f"top_{amount}_{c.from_user.id}", currency="XTR", provider_token="",
        prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)])

@dp_shop.message(F.successful_payment)
async def paid_topup(m: Message):
    parts = m.successful_payment.invoice_payload.split("_")
    if parts[0] == "top":
        amount = int(parts[1])
        user = u(m.from_user.id)
        user['balance'] += amount
        save_db()
        await m.answer(
            f"✅ Баланс пополнен!\n\nЗачислено: {amount}⭐\nТекущий баланс: {user['balance']}⭐",
            reply_markup=kb_main(m.from_user.id)
        )

@dp_shop.callback_query(F.data == "promo")
async def cb_promo(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await state.set_state(ShopStates.promo)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="main")]])
    await c.message.edit_text("🎁 Введите промокод:", reply_markup=kb)

@dp_shop.message(ShopStates.promo)
async def handle_promo(m: Message, state: FSMContext):
    await state.clear()
    code = m.text.strip().upper()
    user = u(m.from_user.id)
    if code in user['used_promos']:
        return await m.answer("❌ Вы уже использовали этот промокод!", reply_markup=kb_main(m.from_user.id))
    if code in promo_codes:
        bonus = promo_codes[code]
        user['balance'] += bonus
        user['used_promos'].append(code)
        save_db()
        await m.answer(f"✅ Промокод активирован!\n🎁 Начислено: {bonus}⭐\nБаланс: {user['balance']}⭐",
            reply_markup=kb_main(m.from_user.id))
    else:
        await m.answer("❌ Неверный промокод!", reply_markup=kb_main(m.from_user.id))

@dp_shop.callback_query(F.data == "my_orders")
async def cb_my_orders(c: CallbackQuery):
    await c.answer()
    user = u(c.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main")]])
    if not user['orders']:
        return await c.message.edit_text("📦 У вас пока нет заказов.", reply_markup=kb)
    text = "📦 Ваши заказы:\n\n"
    for o in user['orders'][-10:]:
        text += f"🆔 №{o['id']} | {o['item']} | {o['price']}⭐ | {o['date']}\n"
    await c.message.edit_text(text, reply_markup=kb)

@dp_shop.callback_query(F.data == "stats")
async def cb_stats(c: CallbackQuery):
    await c.answer()
    total_stock = sum(v['stock'] for v in CATALOG.values())
    await c.message.edit_text(
        f"📊 Статистика\n\n"
        f"👥 Пользователей: {len(users)}\n"
        f"📦 Товаров в наличии: {total_stock}\n"
        f"🛍 Заказов: {len(orders)}\n\n"
        f"Бангладеш: {CATALOG['bd']['stock']} шт.\n"
        f"Канада: {CATALOG['ca']['stock']} шт.\n"
        f"Россия: {CATALOG['ru']['stock']} шт.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main")]])
    )

@dp_shop.callback_query(F.data == "about")
async def cb_about(c: CallbackQuery):
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Написать нам", url="https://t.me/ownnadd")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main")]
    ])
    await c.message.edit_text(
        "ℹ️ О магазине\n\n🏪 Продаём Telegram-аккаунты с 2024 года\n"
        "✅ Гарантия\n⚡ Выдача после оплаты\n"
        "🔒 Оплата через Stars\n💬 Поддержка: @ownnadd",
        reply_markup=kb
    )

@dp_shop.callback_query(F.data == "admin")
async def cb_admin(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("🚫 Нет доступа!", show_alert=True)
    await c.answer()
    await c.message.edit_text("⚙️ Админ панель", reply_markup=kb_admin())

@dp_shop.callback_query(F.data == "adm_stats")
async def adm_stats(c: CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer("🚫")
    await c.answer()
    total_earned = sum(o['price'] for o in orders)
    banned = sum(1 for ud in users.values() if ud.get('banned'))
    await c.message.edit_text(
        f"📊 Статистика (Админ)\n\n"
        f"👥 Пользователей: {len(users)}\n"
        f"🚫 Заблокировано: {banned}\n"
        f"🛍 Заказов: {len(orders)}\n"
        f"💰 Оборот: {total_earned}⭐\n\n"
        f"📦 Склад:\n"
        f"Бангладеш: {CATALOG['bd']['stock']} шт.\n"
        f"Канада: {CATALOG['ca']['stock']} шт.\n"
        f"Россия: {CATALOG['ru']['stock']} шт.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]])
    )

@dp_shop.callback_query(F.data == "adm_broadcast")
async def adm_broadcast(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id): return await c.answer("🚫")
    await c.answer()
    await state.set_state(ShopStates.broadcast)
    await c.message.edit_text("📢 Введите текст рассылки:", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="admin")]]))

@dp_shop.message(ShopStates.broadcast)
async def do_broadcast(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await state.clear()
    sent, failed = 0, 0
    for uid in users:
        try:
            await shop_bot.send_message(uid, f"📢 Сообщение от администратора:\n\n{m.text}")
            sent += 1
        except: failed += 1
    await m.answer(f"✅ Рассылка завершена!\n📤 Отправлено: {sent}\n❌ Не доставлено: {failed}", reply_markup=kb_main(m.from_user.id))

@dp_shop.callback_query(F.data == "adm_users")
async def adm_users(c: CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer("🚫")
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Забанить", callback_data="adm_ban"),
         InlineKeyboardButton(text="✅ Разбанить", callback_data="adm_unban")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]
    ])
    text = f"👥 Пользователи ({len(users)}):\n\n"
    for uid, ud in list(users.items())[-10:]:
        status = "🚫" if ud.get('banned') else "✅"
        text += f"{status} {uid} | @{ud.get('username','?')} | {ud['balance']}⭐ | {len(ud['orders'])} заказов\n"
    await c.message.edit_text(text, reply_markup=kb)

@dp_shop.message(Command("ban"))
async def cmd_ban(m: Message):
    if not is_admin(m.from_user.id): return
    args = m.text.split()
    if len(args) < 2: return await m.answer("Использование: /ban <user_id>")
    u(int(args[1]))['banned'] = True
    save_db()
    await m.answer(f"🚫 Пользователь {args[1]} заблокирован.")

@dp_shop.message(Command("unban"))
async def cmd_unban(m: Message):
    if not is_admin(m.from_user.id): return
    args = m.text.split()
    if len(args) < 2: return await m.answer("Использование: /unban <user_id>")
    u(int(args[1]))['banned'] = False
    save_db()
    await m.answer(f"✅ Пользователь {args[1]} разблокирован.")

@dp_shop.callback_query(F.data == "adm_stock")
async def adm_stock(c: CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer("🚫")
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Бангладеш", callback_data="stock_bd"),
         InlineKeyboardButton(text="➕ Канада", callback_data="stock_ca"),
         InlineKeyboardButton(text="➕ Россия", callback_data="stock_ru")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]
    ])
    await c.message.edit_text(
        f"📦 Управление складом\n\n"
        f"Бангладеш: {CATALOG['bd']['stock']} шт.\n"
        f"Канада: {CATALOG['ca']['stock']} шт.\n"
        f"Россия: {CATALOG['ru']['stock']} шт.",
        reply_markup=kb
    )

@dp_shop.callback_query(F.data.startswith("stock_"))
async def stock_add(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id): return await c.answer("🚫")
    await c.answer()
    k = c.data[6:]
    await state.update_data(stock_key=k)
    await state.set_state(ShopStates.add_stock)
    await c.message.edit_text(f"Введите количество для добавления ({CATALOG[k]['name']}):", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="adm_stock")]]))

@dp_shop.message(ShopStates.add_stock)
async def do_add_stock(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    data = await state.get_data()
    await state.clear()
    try:
        k = data['stock_key']
        CATALOG[k]['stock'] += int(m.text)
        await m.answer(f"✅ Добавлено {m.text} шт. к {CATALOG[k]['name']}\nСклад: {CATALOG[k]['stock']} шт.", reply_markup=kb_main(m.from_user.id))
    except:
        await m.answer("❌ Введите число!", reply_markup=kb_main(m.from_user.id))

@dp_shop.callback_query(F.data == "adm_give")
async def adm_give(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id): return await c.answer("🚫")
    await c.answer()
    await state.set_state(ShopStates.give_balance)
    await c.message.edit_text("💰 Введите: <user_id> <сумма>\nПример: 123456789 100", 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Отмена", callback_data="admin")]]))

@dp_shop.message(ShopStates.give_balance)
async def do_give_balance(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id): return
    await state.clear()
    try:
        parts = m.text.split()
        uid, amount = int(parts[0]), int(parts[1])
        u(uid)['balance'] += amount
        save_db()
        await m.answer(f"✅ Выдано {amount}⭐ пользователю {uid}", reply_markup=kb_main(m.from_user.id))
        try:
            await shop_bot.send_message(uid, f"🎁 Администратор начислил вам {amount}⭐!\nВаш баланс: {u(uid)['balance']}⭐")
        except: pass
    except:
        await m.answer("❌ Ошибка. Формат: <user_id> <сумма>", reply_markup=kb_main(m.from_user.id))

@dp_shop.callback_query(F.data == "adm_promos")
async def adm_promos(c: CallbackQuery):
    if not is_admin(c.from_user.id): return await c.answer("🚫")
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]])
    text = "🎫 Активные промокоды:\n\n"
    for code, bonus in promo_codes.items():
        text += f"🏷 {code} — {bonus}⭐\n"
    text += "\n💡 /addpromo КОД СУММА — добавить\n💡 /delpromo КОД — удалить"
    await c.message.edit_text(text, reply_markup=kb)

@dp_shop.message(Command("addpromo"))
async def cmd_addpromo(m: Message):
    if not is_admin(m.from_user.id): return
    args = m.text.split()
    if len(args) < 3: return await m.answer("Использование: /addpromo КОД СУММА")
    promo_codes[args[1].upper()] = int(args[2])
    save_db()
    await m.answer(f"✅ Промокод {args[1].upper()} на {args[2]}⭐ добавлен!")

@dp_shop.message(Command("delpromo"))
async def cmd_delpromo(m: Message):
    if not is_admin(m.from_user.id): return
    args = m.text.split()
    if len(args) < 2: return await m.answer("Использование: /delpromo КОД")
    code = args[1].upper()
    if code in promo_codes:
        del promo_codes[code]
        save_db()
        await m.answer(f"✅ Промокод {code} удалён.")
    else:
        await m.answer("❌ Промокод не найден.")

@dp_shop.callback_query(F.data.in_({"adm_ban", "adm_unban"}))
async def adm_ban_hint(c: CallbackQuery):
    cmd = "/ban" if c.data == "adm_ban" else "/unban"
    await c.answer(f"Используйте команду {cmd} <user_id>", show_alert=True)

# ==================== БОТ №2: ОТПРАВКА ПОДАРКОВ (ВСЁ ПО КНОПКАМ) ====================

user_clients = {}
user_sessions = {}

class UserBotStates(StatesGroup):
    wait_phone = State()
    wait_code = State()
    wait_password = State()
    wait_gift_choice = State()
    wait_target = State()
    wait_comment = State()

userbot_bot = Bot(token=BOT_TOKEN_USERBOT)
dp_userbot = Dispatcher(storage=MemoryStorage())

# Клавиатуры для второго бота
def kb_start():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Отправить подарок", callback_data="send_gift")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])

def kb_gifts():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Новый подарок", callback_data="gift_1")],
        [InlineKeyboardButton(text="🐻 Мишка 8 марта", callback_data="gift_2")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def kb_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def kb_phone():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def kb_code():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def kb_target():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def kb_comment():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_comment")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

@dp_userbot.message(CommandStart())
async def start_userbot(m: Message, state: FSMContext):
    await state.clear()
    if m.from_user.id in user_clients:
        try:
            await user_clients[m.from_user.id].disconnect()
        except:
            pass
        del user_clients[m.from_user.id]
    
    await m.answer(
        "🤖 <b>Бот для отправки подарков</b>\n\n"
        "Я помогу вам отправить подарок от вашего имени.\n\n"
        "🔐 Для начала нужно войти в ваш аккаунт Telegram.\n\n"
        "Нажмите на кнопку ниже:",
        reply_markup=kb_start(),
        parse_mode="HTML"
    )

@dp_userbot.callback_query(F.data == "cancel")
async def cancel_userbot(c: CallbackQuery, state: FSMContext):
    await state.clear()
    if c.from_user.id in user_clients:
        try:
            await user_clients[c.from_user.id].disconnect()
        except:
            pass
        del user_clients[c.from_user.id]
    await c.answer("✅ Отменено")
    await c.message.edit_text("✅ Операция отменена. Нажмите /start для новой.", reply_markup=None)

@dp_userbot.callback_query(F.data == "send_gift")
async def send_gift_start(c: CallbackQuery, state: FSMContext):
    await c.answer()
    user_id = c.from_user.id
    
    if user_id in user_clients and user_clients[user_id].is_connected():
        await state.update_data(user_id=user_id)
        await state.set_state(UserBotStates.wait_gift_choice)
        await c.message.edit_text(
            "🎁 Выбери подарок для отправки:",
            reply_markup=kb_gifts()
        )
    else:
        await state.set_state(UserBotStates.wait_phone)
        await c.message.edit_text(
            "🔐 Для отправки подарков нужно войти в аккаунт Telegram.\n\n"
            "Введите ваш номер телефона в формате +7XXXXXXXXXX\n\n"
            "Напишите номер в чат:",
            reply_markup=kb_phone()
        )

@dp_userbot.message(UserBotStates.wait_phone)
async def process_phone(m: Message, state: FSMContext):
    phone = m.text.strip()
    if not phone.startswith('+'):
        phone = '+' + phone
    
    try:
        client = TelegramClient(f'user_{m.from_user.id}', 34777093, '344a0bf5882aa3b71e9c15e9e1cb6c52')
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            user_clients[m.from_user.id] = client
            user_sessions[m.from_user.id] = phone
            await state.update_data(phone=phone)
            await state.set_state(UserBotStates.wait_code)
            await m.answer(
                "✅ Код отправлен!\n\n"
                "Введите код из Telegram в чат:",
                reply_markup=kb_code()
            )
        else:
            user_clients[m.from_user.id] = client
            await state.update_data(phone=phone)
            await state.set_state(UserBotStates.wait_gift_choice)
            await m.answer(
                "✅ Уже авторизован!\n\n🎁 Выбери подарок:",
                reply_markup=kb_gifts()
            )
    except Exception as e:
        await m.answer(f"❌ Ошибка: {e}\nПопробуй ещё раз", reply_markup=kb_phone())

@dp_userbot.message(UserBotStates.wait_code)
async def process_code(m: Message, state: FSMContext):
    code = m.text.strip()
    data = await state.get_data()
    client = user_clients.get(m.from_user.id)
    
    if not client:
        await m.answer("❌ Сессия потеряна. Нажмите /start", reply_markup=kb_start())
        await state.clear()
        return
    
    try:
        await client.sign_in(data['phone'], code)
        await state.set_state(UserBotStates.wait_gift_choice)
        await m.answer(
            "✅ Успешный вход!\n\n🎁 Выбери подарок:",
            reply_markup=kb_gifts()
        )
    except Exception as e:
        if 'password' in str(e).lower():
            await state.set_state(UserBotStates.wait_password)
            await m.answer(
                "🔐 Введите пароль двухфакторной авторизации:",
                reply_markup=kb_code()
            )
        else:
            await m.answer(f"❌ Ошибка: {e}\nПопробуй ещё раз", reply_markup=kb_phone())

@dp_userbot.message(UserBotStates.wait_password)
async def process_password(m: Message, state: FSMContext):
    password = m.text.strip()
    client = user_clients.get(m.from_user.id)
    
    if not client:
        await m.answer("❌ Сессия потеряна. Нажмите /start", reply_markup=kb_start())
        await state.clear()
        return
    
    try:
        await client.sign_in(password=password)
        await state.set_state(UserBotStates.wait_gift_choice)
        await m.answer(
            "✅ Успешный вход!\n\n🎁 Выбери подарок:",
            reply_markup=kb_gifts()
        )
    except Exception as e:
        await m.answer(f"❌ Ошибка: {e}", reply_markup=kb_phone())

@dp_userbot.callback_query(UserBotStates.wait_gift_choice, F.data.startswith("gift_"))
async def process_gift_choice(c: CallbackQuery, state: FSMContext):
    await c.answer()
    choice = c.data.split("_")[1]
    
    if choice not in GIFTS:
        await c.message.answer("❌ Неверный выбор", reply_markup=kb_gifts())
        return
    
    await state.update_data(gift_id=GIFTS[choice]["id"], gift_name=GIFTS[choice]["name"])
    await state.set_state(UserBotStates.wait_target)
    await c.message.edit_text(
        "👤 Введите @username пользователя, кому отправить подарок:\n\n"
        "Пример: @durov\n\n"
        "Напишите username в чат:",
        reply_markup=kb_target()
    )

@dp_userbot.message(UserBotStates.wait_target)
async def process_target(m: Message, state: FSMContext):
    target = m.text.strip()
    if not target.startswith('@'):
        await m.answer("❌ Username должен начинаться с @\nПример: @durov", reply_markup=kb_target())
        return
    
    await state.update_data(target=target)
    await state.set_state(UserBotStates.wait_comment)
    await m.answer(
        "💬 Введите комментарий к подарку:\n\n"
        "Напишите текст в чат, или нажмите 'Пропустить'",
        reply_markup=kb_comment()
    )

@dp_userbot.callback_query(F.data == "skip_comment")
async def skip_comment(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await process_final(c.message, state, c.from_user.id, "Подарок от пользователя")

@dp_userbot.message(UserBotStates.wait_comment)
async def process_comment(m: Message, state: FSMContext):
    comment = m.text.strip()
    await process_final(m, state, m.from_user.id, comment)

async def process_final(message, state, user_id, comment):
    data = await state.get_data()
    client = user_clients.get(user_id)
    
    if not client:
        await message.answer("❌ Сессия потеряна. Нажмите /start", reply_markup=kb_start())
        await state.clear()
        return
    
    try:
        target_input = data['target']
        entity = await client.get_entity(target_input)
        
        result = await client.send_gift(
            user_id=entity.id,
            gift_id=data['gift_id'],
            text=comment
        )
        
        if result:
            await message.answer(
                f"✅ Подарок {data['gift_name']} отправлен пользователю {data['target']}!\n\n"
                f"💬 Комментарий: {comment}\n\n"
                f"Нажмите /start для новой отправки",
                reply_markup=None
            )
        else:
            await message.answer("❌ Ошибка при отправке подарка", reply_markup=kb_start())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}\nПроверьте правильность username", reply_markup=kb_target())
        return
    
    # Отключаем клиент после отправки
    try:
        await client.disconnect()
    except:
        pass
    if user_id in user_clients:
        del user_clients[user_id]
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await state.clear()

# ==================== ЗАПУСК ====================

async def main():
    load_db()
    print("✅ Бот магазина запущен")
    print("✅ Бот для отправки подарков запущен")
    
    await asyncio.gather(
        dp_shop.start_polling(shop_bot),
        dp_userbot.start_polling(userbot_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())