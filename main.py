import asyncio
import logging
import random
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

class Game:
    def __init__(self, user_id, mines_count):
        self.user_id = user_id
        self.mines_count = mines_count
        self.rows = 4
        self.cols = 4
        self.total = self.rows * self.cols
        self.safe_count = self.total - mines_count
        self.opened = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.mines = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        
        positions = list(range(self.total))
        random.shuffle(positions)
        for i in range(mines_count):
            pos = positions[i]
            r = pos // self.cols
            c = pos % self.cols
            self.mines[r][c] = True
        
        self.game_over = False
        self.won = False
        self.opened_count = 0

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

    def make_board(self, show_all=False):
        buttons = []
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                if show_all or self.opened[i][j]:
                    if self.mines[i][j]:
                        text = "💣"
                    else:
                        text = "⬜"
                    row.append(InlineKeyboardButton(text=text, callback_data="ignore"))
                else:
                    row.append(InlineKeyboardButton(text="❓", callback_data=f"cell_{i}_{j}"))
            buttons.append(row)
        
        buttons.append([InlineKeyboardButton(text="🔄", callback_data="new_game")])
        buttons.append([InlineKeyboardButton(text="🏠", callback_data="menu")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)

def start_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮", callback_data="play")]
    ])

def mines_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2", callback_data="mines_2")],
        [InlineKeyboardButton(text="4", callback_data="mines_4")],
        [InlineKeyboardButton(text="8", callback_data="mines_8")]
    ])

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer("🎲", reply_markup=start_kb())

@dp.callback_query(F.data == "menu")
async def menu(cb: CallbackQuery):
    if cb.from_user.id in games:
        games.pop(cb.from_user.id)
    await cb.message.answer("🎲", reply_markup=start_kb())
    await cb.answer()

@dp.callback_query(F.data == "play")
async def play(cb: CallbackQuery):
    await cb.message.answer("🎲", reply_markup=mines_kb())
    await cb.answer()

@dp.callback_query(F.data.startswith("mines_"))
async def set_mines(cb: CallbackQuery):
    mines_count = int(cb.data.split("_")[1])
    user_id = cb.from_user.id
    
    game = Game(user_id, mines_count)
    games[user_id] = game
    
    await cb.message.answer("🎲", reply_markup=game.make_board())
    await cb.answer()

@dp.callback_query(F.data.startswith("cell_"))
async def cell(cb: CallbackQuery):
    user_id = cb.from_user.id
    
    if user_id not in games:
        await cb.answer("❌")
        return
    
    game = games[user_id]
    
    if game.game_over:
        await cb.answer("❌")
        return
    
    try:
        _, r, c = cb.data.split("_")
        r, c = int(r), int(c)
    except:
        await cb.answer("❌")
        return
    
    result = game.open_cell(r, c)
    
    if result == "already":
        await cb.answer("⚠️")
        return
    
    await cb.message.edit_reply_markup(reply_markup=game.make_board())
    
    if result == "mine":
        await bot.send_message(user_id, "💥", reply_markup=start_kb())
        games.pop(user_id, None)
    elif game.won:
        await bot.send_message(user_id, "🎉", reply_markup=start_kb())
        games.pop(user_id, None)
    
    await cb.answer()

@dp.callback_query(F.data == "new_game")
async def new_game(cb: CallbackQuery):
    user_id = cb.from_user.id
    games.pop(user_id, None)
    await play(cb)

@dp.callback_query(F.data == "ignore")
async def ignore(cb: CallbackQuery):
    await cb.answer()

async def main():
    try:
        log.info("Запуск бота...")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()
        log.info("Бот остановлен")

if __name__ == '__main__':
    asyncio.run(main())
