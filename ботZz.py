import logging
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

API_TOKEN = '8679806194:AAH35zUFUYhnHWnL210bRwrcTsD_p3ZZM9A'

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

games = {}

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('database.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 1500,
        last_daily TEXT
    )
''')
conn.commit()

def get_balance(user_id):
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute('INSERT INTO users (user_id, balance) VALUES (?, ?)', (user_id, 1500))
        conn.commit()
        return 1500

def update_balance(user_id, amount):
    current = get_balance(user_id)
    new_balance = current + amount
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    conn.commit()
    return new_balance

def can_take_daily(user_id):
    cursor.execute('SELECT last_daily FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result and result[0]:
        last = datetime.fromisoformat(result[0])
        if datetime.now() - last < timedelta(days=1):
            return False
    return True

def set_daily_taken(user_id):
    cursor.execute('UPDATE users SET last_daily = ? WHERE user_id = ?', (datetime.now().isoformat(), user_id))
    conn.commit()

# ========== АДМИНЫ ==========
ADMIN_IDS = [4061]

# ========== ИГРА ==========
class Game:
    def __init__(self, user_id, mines_count, bet):
        self.user_id = user_id
        self.mines_count = mines_count
        self.bet = bet
        self.rows = 4
        self.cols = 4
        self.total = self.rows * self.cols
        self.safe_count = self.total - mines_count
        self.opened = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.mines = [[False for _ in range(self.cols)] for _ in range(self.rows)]

        mine_positions = random.sample(range(self.total), mines_count)
        for pos in mine_positions:
            r = pos // self.cols
            c = pos % self.cols
            self.mines[r][c] = True

        self.lost = False
        self.won = False

    def open_cell(self, r, c):
        if self.opened[r][c]:
            return "already"
        self.opened[r][c] = True

        if self.mines[r][c]:
            self.lost = True
            return "mine"
        else:
            opened_safe = sum(
                1 for i in range(self.rows)
                for j in range(self.cols)
                if self.opened[i][j] and not self.mines[i][j]
            )
            if opened_safe == self.safe_count:
                self.won = True
            return "safe"

    def make_board(self, show_all=False):
        buttons = []
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                text = "❓"
                cb = f"cell_{i}_{j}"
                if self.opened[i][j] or show_all:
                    if self.mines[i][j]:
                        text = "💣"
                    else:
                        text = "💎"
                    cb = "ignore"
                row.append(InlineKeyboardButton(text=text, callback_data=cb))
            buttons.append(row)

        if self.won:
            buttons.append([InlineKeyboardButton(text="✨ Забрать выигрыш", callback_data="collect")])

        buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def calc_win(self):
        return self.bet * self.mines_count * 2

# ========== КЛАВИАТУРЫ ==========
def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть", callback_data="play")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily")]
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu")]
    ])

def mines_kb(bet):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 мины 💥 (x4)", callback_data=f"mines_2_{bet}")],
        [InlineKeyboardButton(text="4 мины 💥 (x8)", callback_data=f"mines_4_{bet}")],
        [InlineKeyboardButton(text="8 мин 💥 (x16)", callback_data=f"mines_8_{bet}")]
    ])

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def start(msg: Message):
    user_id = msg.from_user.id
    balance = get_balance(user_id)
    await msg.answer(
        f"<b>Привет, {msg.from_user.first_name}!</b>\n\n"
        f"💰 Баланс: {balance} Gram\n\n"
        f"Игра «Мины» — делай ставку и выигрывай!",
        reply_markup=start_kb()
    )

@dp.message(Command("balance"))
async def balance_cmd(msg: Message):
    bal = get_balance(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {bal} Gram", reply_markup=back_kb())

@dp.message(Command("admin"))
async def admin_cmd(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ Нет доступа")
        return
    await msg.answer("👑 Админ-панель\n\n/give ID сумма - выдать граммы")

@dp.message(Command("give"))
async def give_cmd(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    args = msg.text.split()
    if len(args) != 3:
        await msg.answer("❌ /give 123456789 500")
        return
    try:
        user_id = int(args[1])
        amount = int(args[2])
        update_balance(user_id, amount)
        await msg.answer(f"✅ Выдано {amount} Gram пользователю {user_id}")
    except:
        await msg.answer("❌ Ошибка")

@dp.callback_query(F.data == "menu")
async def menu(cb: CallbackQuery):
    user_id = cb.from_user.id
    balance = get_balance(user_id)
    await cb.message.answer(
        f"💰 Баланс: {balance} Gram\n\nГлавное меню:",
        reply_markup=start_kb()
    )
    await cb.answer()

@dp.callback_query(F.data == "balance")
async def balance(cb: CallbackQuery):
    bal = get_balance(cb.from_user.id)
    await cb.message.answer(f"💰 Баланс: {bal} Gram", reply_markup=back_kb())
    await cb.answer()

@dp.callback_query(F.data == "daily")
async def daily(cb: CallbackQuery):
    user_id = cb.from_user.id
    if can_take_daily(user_id):
        new_balance = update_balance(user_id, 2500)
        set_daily_taken(user_id)
        await cb.message.answer(
            f"🎁 Получено 2500 Gram!\n"
            f"💰 Баланс: {new_balance} Gram",
            reply_markup=back_kb()
        )
    else:
        cursor.execute('SELECT balance, last_daily FROM users WHERE user_id = ?', (user_id,))
        bal, last = cursor.fetchone()
        last_dt = datetime.fromisoformat(last)
        next_day = (last_dt + timedelta(days=1)).strftime("%d.%m.%Y в %H:%M")
        await cb.message.answer(
            f"⏳ Ты уже получал бонус сегодня!\n"
            f"💰 Твой баланс: {bal} Gram\n"
            f"🔜 Следующий бонус доступен: {next_day}",
            reply_markup=back_kb()
        )
    await cb.answer()

@dp.callback_query(F.data == "play")
async def play(cb: CallbackQuery):
    await cb.message.answer("💰 <b>Укажи ставку</b>\n\nПример: `мины 100`")
    await cb.answer()

@dp.message(lambda msg: msg.text and msg.text.lower().startswith("мины"))
async def mines_command(msg: Message):
    user_id = msg.from_user.id
    try:
        bet = int(msg.text.split()[1])
    except:
        await msg.answer("❌ Пример: `мины 100`")
        return

    balance = get_balance(user_id)
    if bet < 10:
        await msg.answer("❌ Минимальная ставка: 10 Gram")
        return
    if bet > balance:
        await msg.answer(f"❌ Недостаточно средств! Баланс: {balance} Gram")
        return

    await msg.answer(f"✅ Ставка: {bet} Gram\n\n🎲 Выбери сложность:", reply_markup=mines_kb(bet))

@dp.callback_query(F.data.startswith("mines_"))
async def set_mines(cb: CallbackQuery):
    try:
        _, mines, bet = cb.data.split("_")
        mines = int(mines)
        bet = int(bet)
    except:
        await cb.answer("Ошибка")
        return

    user_id = cb.from_user.id
    balance = get_balance(user_id)
    if bet > balance:
        await cb.answer(f"❌ Недостаточно средств! Баланс: {balance} Gram", show_alert=True)
        return

    update_balance(user_id, -bet)
    game = Game(user_id, mines, bet)
    games[user_id] = game

    await cb.message.answer(
        f"🎲 <b>Игра началась!</b>\n\n"
        f"💰 Ставка: {bet} Gram\n"
        f"🏆 Выигрыш: {game.calc_win()} Gram\n\n"
        f"Открывай клетки 💎",
        reply_markup=game.make_board()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("cell_"))
async def cell(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in games:
        await cb.answer("Нет активной игры. Напиши /start", show_alert=True)
        return

    game = games[user_id]
    if game.lost or game.won:
        await cb.answer("Игра уже окончена!")
        return

    try:
        _, r, c = cb.data.split("_")
        r, c = int(r), int(c)
    except:
        await cb.answer("Ошибка")
        return

    result = game.open_cell(r, c)

    if result == "already":
        await cb.answer("⚠️ Эта клетка уже открыта!")
        return

    if result == "mine":
        try:
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=cb.message.message_id,
                reply_markup=game.make_board(show_all=True)
            )
        except:
            pass
        await bot.send_message(
            user_id,
            f"💥 <b>Ты попал на мину!</b>\n\n"
            f"💰 Ставка: {game.bet} Gram\n"
            f"💸 Потеряно: {game.bet} Gram",
            reply_markup=start_kb()
        )
        games.pop(user_id, None)
    else:
        try:
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=cb.message.message_id,
                reply_markup=game.make_board()
            )
        except:
            pass

        if game.won:
            win = game.calc_win()
            new_balance = update_balance(user_id, win)
            await bot.send_message(
                user_id,
                f"🎉 <b>ПОБЕДА!</b> 🎉\n\n"
                f"💰 Ставка: {game.bet} Gram\n"
                f"🏆 Выигрыш: {win} Gram\n"
                f"💎 Новый баланс: {new_balance} Gram",
                reply_markup=start_kb()
            )
            games.pop(user_id, None)

    await cb.answer()

@dp.callback_query(F.data == "collect")
async def collect(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in games:
        await cb.answer("Нет активной игры!")
        return

    game = games[user_id]
    if not game.won:
        await cb.answer("Ты ещё не выиграл! Открой все безопасные клетки.")
        return

    win = game.calc_win()
    new_balance = update_balance(user_id, win)
    await bot.send_message(
        user_id,
        f"✨ <b>Ты забрал выигрыш!</b>\n\n"
        f"🏆 +{win} Gram\n"
        f"💰 Новый баланс: {new_balance} Gram",
        reply_markup=start_kb()
    )
    games.pop(user_id, None)
    await cb.answer()

# ========== ЗАПУСК ==========
async def main():
    try:
        log.info("Запуск бота...")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        log.info("Бот остановлен")

if __name__ == '__main__':
    asyncio.run(main())
