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

# ========== АДМИНЫ ==========
ADMIN_IDS = [8364328997]

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
        
        # Расставляем мины
        positions = list(range(self.total))
        random.shuffle(positions)
        for i in range(mines_count):
            pos = positions[i]
            r = pos // self.cols
            c = pos % self.cols
            self.mines[r][c] = True
        
        self.opened_count = 0
        self.game_over = False
        self.won = False
    
    def open_cell(self, r, c):
        if self.game_over:
            return "game_over"
        if self.opened[r][c]:
            return "already"
        
        self.opened[r][c] = True
        
        if self.mines[r][c]:
            self.game_over = True
            return "mine"
        else:
            self.opened_count += 1
            if self.opened_count == self.safe_count:
                self.game_over = True
                self.won = True
            return "safe"
    
    def get_current_win(self):
        # Простая формула: ставка * (открытые_клетки / безопасные_клетки) * множитель_сложности
        if self.opened_count == 0:
            return 0
        multiplier = self.mines_count  # 2, 4 или 8
        win = int(self.bet * (self.opened_count / self.safe_count) * multiplier)
        return max(win, 0)
    
    def get_max_win(self):
        return self.bet * self.mines_count
    
    def make_board(self, show_all=False):
        buttons = []
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                if show_all:
                    if self.mines[i][j]:
                        text = "💣"
                    else:
                        text = "💎"
                    row.append(InlineKeyboardButton(text=text, callback_data="ignore"))
                elif self.opened[i][j]:
                    if self.mines[i][j]:
                        text = "💣"
                    else:
                        text = "💎"
                    row.append(InlineKeyboardButton(text=text, callback_data="ignore"))
                else:
                    row.append(InlineKeyboardButton(text="❓", callback_data=f"cell_{i}_{j}"))
            buttons.append(row)
        
        if not self.game_over and self.opened_count > 0:
            current_win = self.get_current_win()
            buttons.append([InlineKeyboardButton(text=f"✨ Забрать {current_win} Gram", callback_data="collect")])
        
        buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

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

def mines_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 мины (x2)", callback_data="mines_2")],
        [InlineKeyboardButton(text="4 мины (x4)", callback_data="mines_4")],
        [InlineKeyboardButton(text="8 мин (x8)", callback_data="mines_8")]
    ])

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def start(msg: Message):
    user_id = msg.from_user.id
    balance = get_balance(user_id)
    await msg.answer(
        f"<b>Привет, {msg.from_user.first_name}!</b>\n\n"
        f"💰 Баланс: {balance} Gram\n\n"
        f"🎲 Игра «Мины»:\n"
        f"• Сделай ставку\n"
        f"• Выбери сложность\n"
        f"• Открывай клетки\n"
        f"• Забери выигрыш в любой момент!",
        reply_markup=start_kb()
    )

@dp.message(Command("balance"))
async def balance_cmd(msg: Message):
    bal = get_balance(msg.from_user.id)
    await msg.answer(f"💰 Баланс: {bal} Gram", reply_markup=back_kb())

@dp.message(Command("id"))
async def get_id(msg: Message):
    await msg.answer(f"🆔 Твой ID: `{msg.from_user.id}`")

@dp.message(Command("admin"))
async def admin_cmd(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("⛔ Нет доступа")
        return
    await msg.answer("👑 Админ-панель\n\n/give ID сумма")

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
        current = get_balance(user_id)
        set_balance(user_id, current + amount)
        await msg.answer(f"✅ Выдано {amount} Gram\n💰 Новый баланс: {get_balance(user_id)}")
    except:
        await msg.answer("❌ Ошибка")

@dp.callback_query(F.data == "menu")
async def menu(cb: CallbackQuery):
    user_id = cb.from_user.id
    games.pop(user_id, None)
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
        current = get_balance(user_id)
        set_balance(user_id, current + 2500)
        set_daily_taken(user_id)
        await cb.message.answer(
            f"🎁 +2500 Gram!\n"
            f"💰 Новый баланс: {get_balance(user_id)} Gram",
            reply_markup=back_kb()
        )
    else:
        await cb.message.answer(
            f"⏳ Ты уже получал бонус сегодня!\n"
            f"💰 Баланс: {get_balance(user_id)} Gram",
            reply_markup=back_kb()
        )
    await cb.answer()

@dp.callback_query(F.data == "play")
async def play(cb: CallbackQuery):
    await cb.message.answer(
        "💰 <b>Укажи ставку</b>\n\n"
        "Пример: `мины 100`\n"
        "Минимальная ставка: 10 Gram",
        reply_markup=back_kb()
    )
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
        await msg.answer(f"❌ Недостаточно средств!\n💰 Баланс: {balance} Gram")
        return
    
    # Сохраняем ставку во временную переменную
    games[f"bet_{user_id}"] = bet
    await msg.answer(
        f"✅ Ставка: {bet} Gram\n\n"
        f"🎲 Выбери сложность:",
        reply_markup=mines_kb()
    )

@dp.callback_query(F.data.startswith("mines_"))
async def set_mines(cb: CallbackQuery):
    user_id = cb.from_user.id
    
    # Получаем ставку
    bet_key = f"bet_{user_id}"
    if bet_key not in games:
        await cb.answer("❌ Сначала укажи ставку командой «мины X»")
        return
    
    bet = games[bet_key]
    del games[bet_key]
    
    mines_count = int(cb.data.split("_")[1])
    
    # Проверяем баланс ещё раз
    balance = get_balance(user_id)
    if bet > balance:
        await cb.answer(f"❌ Недостаточно средств! Баланс: {balance} Gram", show_alert=True)
        return
    
    # Списываем ставку
    set_balance(user_id, balance - bet)
    
    # Создаём игру
    game = Game(user_id, mines_count, bet)
    games[user_id] = game
    
    await cb.message.answer(
        f"🎲 <b>Игра началась!</b>\n\n"
        f"💰 Ставка: {bet} Gram\n"
        f"💣 Мин: {mines_count}\n"
        f"🏆 Макс. выигрыш: {game.get_max_win()} Gram\n\n"
        f"💎 Открывай клетки!\n"
        f"✨ Чем больше откроешь — тем больше выигрыш!",
        reply_markup=game.make_board()
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("cell_"))
async def cell(cb: CallbackQuery):
    user_id = cb.from_user.id
    
    if user_id not in games:
        await cb.answer("❌ Нет активной игры! Напиши /start")
        return
    
    game = games[user_id]
    
    if game.game_over:
        await cb.answer("Игра уже закончена!")
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
    
    # Обновляем поле
    await cb.message.edit_reply_markup(reply_markup=game.make_board())
    
    if result == "mine":
        await bot.send_message(
            user_id,
            f"💥 <b>Ты попал на мину!</b>\n\n"
            f"💰 Ставка: {game.bet} Gram\n"
            f"💸 Потеряно: {game.bet} Gram",
            reply_markup=start_kb()
        )
        games.pop(user_id, None)
    elif result == "safe" and game.won:
        win = game.get_current_win()
        current_balance = get_balance(user_id)
        set_balance(user_id, current_balance + win)
        await bot.send_message(
            user_id,
            f"🎉 <b>ПОБЕДА!</b> 🎉\n\n"
            f"💰 Ставка: {game.bet} Gram\n"
            f"🏆 Выигрыш: {win} Gram\n"
            f"💎 Новый баланс: {get_balance(user_id)} Gram",
            reply_markup=start_kb()
        )
        games.pop(user_id, None)
    
    await cb.answer()

@dp.callback_query(F.data == "collect")
async def collect(cb: CallbackQuery):
    user_id = cb.from_user.id
    
    if user_id not in games:
        await cb.answer("❌ Нет активной игры!")
        return
    
    game = games[user_id]
    
    if game.game_over:
        await cb.answer("Игра уже закончена!")
        return
    
    win = game.get_current_win()
    if win <= 0:
        await cb.answer("❌ Пока нечего забирать! Открой хотя бы одну клетку.")
        return
    
    current_balance = get_balance(user_id)
    set_balance(user_id, current_balance + win)
    
    await bot.send_message(
        user_id,
        f"✨ <b>Ты забрал выигрыш!</b> ✨\n\n"
        f"💰 Ставка: {game.bet} Gram\n"
        f"🏆 Выигрыш: +{win} Gram\n"
        f"💎 Новый баланс: {get_balance(user_id)} Gram",
        reply_markup=start_kb()
    )
    games.pop(user_id, None)
    await cb.answer()

@dp.callback_query(F.data == "ignore")
async def ignore(cb: CallbackQuery):
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
