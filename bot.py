import asyncio
import logging
from openai import OpenAI
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
from aiohttp import web
import json
import os

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8157670620:AAHbVZuypLOBgtKXn8aVWEJEumJS2gPuelU"
GITHUB_TOKEN = "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"
PORT = int(os.environ.get("PORT", 8080))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Настройка GitHub Models клиента
client = OpenAI(
    api_key=GITHUB_TOKEN,
    base_url="https://models.inference.ai.azure.com"
)

# Доступные модели
MODELS = {
    "llama": {"name": "Llama 3.2", "id": "meta-llama/llama-3.2-3b-instruct"},
    "phi": {"name": "Phi-3.5 Mini", "id": "microsoft/phi-3.5-mini-128k-instruct"},
    "mistral": {"name": "Mistral 7B", "id": "mistralai/mistral-7b-instruct"}
}

def ask_ai(question, model_id):
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": question}],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка: {e}"

def main_keyboard():
    web_app = WebAppInfo(url="https://aibot-production-1712.up.railway.app/webapp")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Открыть чат с ИИ", web_app=web_app)],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")]
    ])

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🤖 Добро пожаловать!\n\nЯ бот с веб-интерфейсом для общения с ИИ.\nИспользую GitHub Models.\n\nНажми на кнопку ниже, чтобы открыть чат.",
        reply_markup=main_keyboard()
    )

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "ℹ️ О боте\n\nИспользует GitHub Models\nМодели: Llama 3.2, Phi-3.5, Mistral 7B\n\nСоздатель: @ownnadd",
        reply_markup=main_keyboard()
    )

async def handle_ask(request):
    try:
        data = await request.json()
        question = data.get('question')
        model_key = data.get('model', 'llama')
        if not question:
            return web.json_response({'error': 'No question'}, status=400)
        model_id = MODELS.get(model_key, MODELS['llama'])['id']
        answer = ask_ai(question, model_id)
        return web.json_response({'answer': answer})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

async def handle_webapp(request):
    with open('index.html', 'r', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='text/html')

async def start_web():
    app = web.Application()
    app.router.add_post('/ask', handle_ask)
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