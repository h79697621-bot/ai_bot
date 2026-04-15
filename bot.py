import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command
from aiohttp import web
import os

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8745927128:AAFR4VfgDKVDAkd8qjiLo78mtVjR6nBxp2s"
ADMIN_ID = 8562793772
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных
conn = sqlite3.connect("game_data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER)")
conn.commit()

def get_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute("INSERT INTO users VALUES (?, ?)", (user_id, 1000))
    conn.commit()
    return 1000

def update_balance(user_id, amount):
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def set_balance(user_id, amount):
    c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def main_keyboard():
    web_app = WebAppInfo(url="https://aibot-production-ea51.up.railway.app/webapp")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💣 Минное поле", web_app=web_app)]
    ])

@dp.message(CommandStart())
async def start(message: Message):
    get_balance(message.from_user.id)
    await message.answer(
        "💣 Добро пожаловать в Минное поле!\n\n"
        "Нажми на кнопку, чтобы начать игру.\n\n"
        "Правила:\n"
        "• Выбери ставку (10, 50, 100, 500)\n"
        "• Открывай клетки, не наступай на мины\n"
        "• Чем больше открыл — тем выше множитель\n"
        "• В любой момент забери выигрыш",
        reply_markup=main_keyboard()
    )

@dp.message(Command("4061"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Нет доступа")
        return
    
    args = message.text.split()
    if len(args) == 1:
        await message.answer(
            "🔧 Админ панель\n\n"
            "Команды:\n"
            "/4061 balance - проверить свой баланс\n"
            "/4061 give 100 - выдать себе 100\n"
            "/4061 give 123456789 50 - выдать пользователю 50"
        )
    elif len(args) == 2 and args[1] == "balance":
        bal = get_balance(ADMIN_ID)
        await message.answer(f"💰 Твой баланс: {bal}")
    elif len(args) == 3 and args[1] == "give":
        try:
            amount = int(args[2])
            update_balance(ADMIN_ID, amount)
            await message.answer(f"✅ Выдано {amount}\n💰 Баланс: {get_balance(ADMIN_ID)}")
        except:
            await message.answer("❌ Ошибка. Используй: /4061 give 100")
    elif len(args) == 4 and args[1] == "give":
        try:
            target = int(args[2])
            amount = int(args[3])
            update_balance(target, amount)
            await message.answer(f"✅ Выдано {amount} пользователю {target}")
            try:
                await bot.send_message(target, f"🎁 Администратор начислил вам {amount} монет!\n💰 Баланс: {get_balance(target)}")
            except:
                pass
        except:
            await message.answer("❌ Ошибка. Используй: /4061 give 123456789 50")

@dp.message(Command("balance"))
async def show_balance(message: Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"💰 Твой баланс: {bal}")

async def handle_webapp(request):
    with open('index.html', 'r', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='text/html')

async def start_web():
    app = web.Application()
    app.router.add_get('/webapp', handle_webapp)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"Веб-сервер запущен на порту {PORT}")

async def main():
    await start_web()
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
