import logging
import random
import asynql
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
    new_balance = get_balance(user_id) + amount
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    conn.commit()
    return new_balance

def set_balance(user_id, amount):
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (amount, user_id))
    conn.commit()

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

# ========== АДМИН ПАНЕЛЬ ==========
ADMIN_IDS = [4061]  # замени на свой ID

# ========== КЛАСС ИГРЫ ==========
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
        self.multiplier = mines_count * 2

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

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def calc_win(self):
        return int(self.bet * self.multiplier)

# ========== КЛАВИАТУРЫ ==========
def start_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть", callback_data="play")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily")]
    ])
    return kb

def admin_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="💸 Выдать граммы", callback_data="admin_give")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu")]
    ])
    return kb

def back_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu")]
    ])
    return kb

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command(commands=["start"]))
async def start(msg: Message):
    user_id = msg.from_user.id
    get_balance(user_id)
    await msg.answer(
        f"<b>Привет, {msg.from_user.first_name}!</b> 🚀\n\n"
        f"💰 Баланс: {get_balance(user_id)} Gram\n\n"
        "Игра «Мины» — выбирай сложность, делай ставку и выигрывай!",
        reply_markup=start_kb()
    )

@dp.message(Command(commands=["admin"]))
async def admin_panel(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ У вас нет доступа к админ-панели.")
        return
    await msg.answer("👑 <b>Админ-панель</b>", reply_markup=admin_kb())

@dp.message(Command(commands=["balance"]))
async def balance_cmd(msg: Message):
    bal = get_balance(msg.from_user.id)
    await msg.answer(f"💰 Ваш баланс: <b>{bal}</b> Gram", reply_markup=back_kb())

@dp.callback_query(F.data == "menu")
async def menu(cb: CallbackQuery):
    await cb.message.answer(
        f"💰 Баланс: {get_balance(cb.from_user.id)} Gram\n\nГлавное меню:",
        reply_markup=start_kb()
    )
    await cb.answer()

@dp.callback_query(F.data == "balance")
async def balance(cb: CallbackQuery):
    bal = get_balance(cb.from_user.id)
    await cb.message.answer(f"💰 Ваш баланс: <b>{bal}</b> Gram", reply_markup=back_kb())
    await cb.answer()

@dp.callback_query(F.data == "daily")
async def daily(cb: CallbackQuery):
    user_id = cb.from_user.id
    if can_take_daily(user_id):
        update_balance(user_id, 2500)
        set_daily_taken(user_id)
        await cb.message.answer(f"🎁 Вы получили 2500 Gram!\n💰 Баланс: {get_balance(user_id)} Gram", reply_markup=back_kb())
    else:
        await cb.message.answer("⏳ Вы уже получали ежедневный бонус. Приходите завтра!", reply_markup=back_kb())
    await cb.answer()

@dp.callback_query(F.data == "play")
async def play(cb: CallbackQuery):
    await cb.message.answer("💎 <b>Укажите ставку</b>\n\nПример: `мины 100` или просто `100`\n\nВыберите сложность после ставки.", reply_markup=back_kb())
    await cb.answer()

@dp.message(lambda msg: msg.text and msg.text.lower().startswith(("мины", "mines")))
async def mines_command(msg: Message):
    user_id = msg.from_user.id
    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("❌ Пример: `мины 100`", reply_markup=back_kb())
        return
    try:
        bet = int(parts[1])
    except:
        await msg.answer("❌ Ставка должна быть числом!", reply_markup=back_kb())
        return

    balance = get_balance(user_id)
    if bet < 10:
        await msg.answer("❌ Минимальная ставка: 10 Gram", reply_markup=back_kb())
        return
    if bet > balance:
        await msg.answer(f"❌ Недостаточно средств! Ваш баланс: {balance} Gram", reply_markup=back_kb())
        return

    await msg.answer(
        f"✅ Ставка: {bet} Gram\n\n"
        "🎲 <b>Выберите сложность:</b>",
        reply_markup=mines_kb(bet)
    )

def mines_kb(bet):
    buttons = [
        [InlineKeyboardButton(text="2 мин 💥 (x4)", callback_data=f"mines_2_{bet}")],
        [InlineKeyboardButton(text="4 мин 💥 (x8)", callback_data=f"mines_4_{bet}")],
        [InlineKeyboardButton(text="8 мин 💥 (x16)", callback_data=f"mines_8_{bet}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.callback_query(F.data.startswith("mines_"))
async def set_mines(cb: CallbackQuery):
    try:
        _, mines, bet = cb.data.split("_")
        mines = int(mines)
        bet = int(bet)
    except:
        await cb.answer("Ошибка!")
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
        f"🎯 Множитель: x{game.multiplier}\n"
        f"🏆 Возможный выигрыш: {game.calc_win()} Gram\n\n"
        f"Открывай клетки 💎",
        reply_markup=game.make_board()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("cell_"))
async def cell(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in games:
        await cb.answer("Игра не найдена. Начните новую командой /start", show_alert=True)
        return

    game = games[user_id]
    if game.lost or game.won:
        await cb.answer("Игра уже окончена!")
        return

    try:
        _, r, c = cb.data.split("_")
        r = int(r)
        c = int(c)
    except:
        await cb.answer("Ошибка!")
        return

    result = game.open_cell(r, c)

    if result == "already":
        await cb.answer("⚠️ Ты уже открыл эту клетку!")
        return

    if result == "mine":
        board = game.make_board(show_all=True)
        try:
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=cb.message.message_id,
                reply_markup=board
            )
        except:
            pass
        await bot.send_message(
            user_id,
            f"💥 <b>Вы подорвались на мине!</b>\n\n"
            f"💰 Ставка: {game.bet} Gram\n"
            f"💸 Потеряно: {game.bet} Gram\n\n"
            f"Попробуйте снова!",
            reply_markup=start_kb()
        )
        games.pop(user_id, None)
    else:
        board = game.make_board()
        try:
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=cb.message.message_id,
                reply_markup=board
            )
        except:
            pass

        if game.won:
            win_amount = game.calc_win()
            update_balance(user_id, win_amount)
            await bot.send_message(
                user_id,
                f"🎉 <b>ПОБЕДА!</b> 🎉\n\n"
                f"💰 Ставка: {game.bet} Gram\n"
                f"🎯 Множитель: x{game.multiplier}\n"
                f"🏆 Выигрыш: {win_amount} Gram\n\n"
                f"💎 Новый баланс: {get_balance(user_id)} Gram",
                reply_markup=start_kb()
            )
            games.pop(user_id, None)

    await cb.answer()

@dp.callback_query(F.data == "collect")
async def collect(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in games:
        await cb.answer("Игра не найдена!")
        return

    game = games[user_id]
    if not game.won:
        await cb.answer("Вы ещё не выиграли!")
        return

    win_amount = game.calc_win()
    update_balance(user_id, win_amount)

    await bot.send_message(
        user_id,
        f"🎉 <b>Вы забрали выигрыш!</b> 🎉\n\n"
        f"💰 Ставка: {game.bet} Gram\n"
        f"🏆 Выигрыш: {win_amount} Gram\n"
        f"💎 Новый баланс: {get_balance(user_id)} Gram",
        reply_markup=start_kb()
    )
    games.pop(user_id, None)
    await cb.answer()

# ========== АДМИН ОБРАБОТЧИКИ ==========
@dp.callback_query(F.data == "admin_stats")
async def admin_stats(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("⛔ Нет доступа")
        return
    cursor.execute('SELECT COUNT(*) FROM users')
    users_count = cursor.fetchone()[0]
    cursor.execute('SELECT SUM(balance) FROM users')
    total_balance = cursor.fetchone()[0] or 0
    await cb.message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"💰 Всего Gram: {total_balance}",
        reply_markup=admin_kb()
    )
    await cb.answer()

@dp.callback_query(F.data == "admin_give")
async def admin_give(cb: CallbackQuery):
    if cb.from_user.id not in ADMIN_IDS:
        await cb.answer("⛔ Нет доступа")
        return
    await cb.message.answer("📝 Введите ID пользователя и сумму через пробел\n\nПример: `123456789 1000`", reply_markup=back_kb())
    await cb.answer()

@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and msg.text and msg.text[0].isdigit())
async def give_grams(msg: Message):
    try:
        user_id, amount = map(int, msg.text.split())
        update_balance(user_id, amount)
        await msg.answer(f"✅ Выдано {amount} Gram пользователю {user_id}\n💰 Новый баланс: {get_balance(user_id)} Gram", reply_markup=admin_kb())
    except:
        await msg.answer("❌ Ошибка! Используйте: `123456789 1000`")

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