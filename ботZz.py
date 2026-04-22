import logging
import random
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.client.bot import DefaultBotProperties
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

API_TOKEN = '8679806194:AAH35zUFUYhnHWnL210bRwrcTsD_p3ZZM9A'

WATERMARK = "\n\nСделано командой cmdserv\nЗаказать бота https://cmdserv.ru"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

games = {}


def add_menu_btn(keyboard):
    new_buttons = keyboard.inline_keyboard.copy()
    new_buttons.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=new_buttons)


def end_kb():
    buttons = [
        InlineKeyboardButton(text="🎮 Играть ещё", callback_data="play"),
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="menu")
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


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


def mines_kb():
    buttons = [
        InlineKeyboardButton(text=f"{mines} мин 💥", callback_data=f"mines_{mines}")
        for mines in [2, 4, 8]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons])
    return add_menu_btn(kb)


def play_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Играть", callback_data="play")]
    ])
    return add_menu_btn(kb)


@dp.message(Command(commands=["start"]))
async def start(msg: Message):
    txt = (
            f"<b>Привет, {msg.from_user.first_name}!</b> 🚀\n\n"
            "Добро пожаловать в <i>игру «Мины»</i> – эпичное приключение, где каждый ход полон адреналина и неожиданных поворотов! 😎\n\n"
            "Приготовьтесь к испытаниям: за каждым поворотом может скрываться как сокровище, так и опасная мина! 💥\n\n"
            "Выберите действие ниже и начните своё приключение!" + WATERMARK
    )
    await msg.answer(txt, reply_markup=play_kb())


@dp.message(Command(commands=["help"]))
async def help(msg: Message):
    txt = (
            "<b>Как играть в «Мины»:</b> 🤓\n\n"
            "1. Нажмите кнопку <b>«Играть»</b> для начала новой игры. 🎮\n"
            "2. Выберите количество мин (от 2 до 8). Чем больше мин – тем выше риск и награда! 💥\n"
            "3. Открывайте клетки поля: если клетка безопасна, она покажет сверкающий алмаз <b>💎</b>.\n"
            "4. Если вы откроете клетку с миной <b>💣</b>, сначала придет анимация взрыва, а затем сообщение о поражении – будьте бдительны! 😱\n"
            "5. После открытия всех безопасных клеток нажмите <b>«✨ Забрать выигрыш»</b>, чтобы получить награду (выигрыш = количество мин * 100 очков). 🏆" + WATERMARK
    )
    await msg.answer(txt, reply_markup=play_kb())


@dp.callback_query(F.data == "menu")
async def menu(cb: CallbackQuery):
    txt = (
            "<b>Главное меню</b> 🌟\n\n"
            "Выберите, что хотите сделать дальше:" + WATERMARK
    )
    await cb.message.answer(txt, reply_markup=play_kb())
    await cb.answer()


@dp.callback_query(F.data == "play")
async def play(cb: CallbackQuery):
    txt = (
            "<b>Выбор сложности</b> 🔥\n\n"
            "Выберите количество мин. Чем больше мин – тем рискованнее игра, но и награда будет выше, если удача на вашей стороне! 🚀" + WATERMARK
    )
    kb = mines_kb()
    await cb.message.answer(txt, reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data.startswith("mines_"))
async def set_mines(cb: CallbackQuery):
    try:
        mines = int(cb.data.split("_")[1])
    except:
        await cb.answer("Неверный выбор мин! 😕")
        return

    user_id = cb.from_user.id
    game = Game(user_id, mines)
    games[user_id] = game
    txt = (
            "<b>Начало игры</b> 🎲\n\n"
            "Каждая клетка скрывает загадку... Будьте осторожны: за одной из них может крыться мина! 💣\n\n"
            "Пусть удача будет на вашей стороне, и вы найдёте несметные сокровища! 💎" + WATERMARK
    )
    await cb.message.answer(txt, reply_markup=game.make_board())
    await cb.answer()


@dp.callback_query(F.data.startswith("cell_"))
async def cell(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in games:
        await cb.answer("Игра не найдена. Нажмите /start для новой игры. 😕", show_alert=True)
        return

    game = games[user_id]
    if game.lost or game.won:
        await cb.answer("Игра уже окончена! 🚫")
        return

    try:
        _, r, c = cb.data.split("_")
        r = int(r)
        c = int(c)
    except:
        await cb.answer("Ошибка координат! 🔧")
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
        except Exception:
            pass
        
        txt = (
                "<b>Ой!</b> Вы раскрыли мину <b>💣</b> и произошёл взрыв... Игра окончена. 😢\n"
                "Хотите сыграть ещё?" + WATERMARK
        )
        await bot.send_message(user_id, txt, reply_markup=end_kb())
        games.pop(user_id, None)
    else:
        board = game.make_board()
        try:
            await bot.edit_message_reply_markup(
                chat_id=user_id,
                message_id=cb.message.message_id,
                reply_markup=board
            )
        except Exception:
            pass
        
        if game.won:
            txt = (
                    "<b>Вау!</b> Все безопасные клетки раскрыты, и вы нашли сокровища! 🎉\n"
                    "Нажмите <b>«✨ Забрать выигрыш»</b>, чтобы получить свою заслуженную награду. 🏆" + WATERMARK
            )
            await bot.send_message(user_id, txt)
    
    await cb.answer()


@dp.callback_query(F.data == "collect")
async def collect(cb: CallbackQuery):
    user_id = cb.from_user.id
    if user_id not in games:
        await cb.answer("Игра не найдена! 😕")
        return

    game = games[user_id]
    if not game.won:
        await cb.answer("Вы ещё не выиграли! 🤔")
        return

    win = game.mines_count * 100
    txt = (
            f"<b>Поздравляем!</b> Вы выиграли <b>{win}</b> очков! 🏆\n"
            "Ваши смелость и решительность принесли вам победу! 🎊\n"
            "Хотите сыграть ещё?" + WATERMARK
    )
    await bot.send_message(user_id, txt, reply_markup=end_kb())
    games.pop(user_id, None)
    await cb.answer()


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