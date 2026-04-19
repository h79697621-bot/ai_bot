import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8707799144:AAEq2DEOP43-V6KOmUdefChhJ6MDPrJY6gQ"
ADMIN_ID = 8516089848
# ===============================

# Хранилище для музыки (в памяти)
music_file_id = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("🔥 Бот активирован!\nСкинь мне аудиофайл, потом напиши /play")
    else:
        await update.message.reply_text("Ты не админ, иди нахуй")

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global music_file_id
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Нет прав")
        return
    
    if music_file_id is None:
        await update.message.reply_text("Сначала скинь музыку боту, сука")
        return
    
    # Здесь можно отправить команду ловушке (но ловушка сама опрашивает)
    await update.message.reply_text("🎵 Команда /play отправлена. Если ловушка активна — музыка включится!")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global music_file_id
    if update.effective_user.id != ADMIN_ID:
        return
    
    audio = update.message.audio
    if audio:
        music_file_id = audio.file_id
        # Сохраняем в файл, чтобы не потерять
        with open("last_music.txt", "w") as f:
            f.write(music_file_id)
        await update.message.reply_text(f"✅ Музыка сохранена!\nФайл: {audio.file_name}\nТеперь используй /play")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("Я понимаю только /start, /play и аудиофайлы")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Бот запущен, сука")
    app.run_polling()

if __name__ == "__main__":
    main()