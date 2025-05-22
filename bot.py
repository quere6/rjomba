import random
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# Словник фраз (які користувач має написати)
PHRASES = {
    "ржомба": "🤣",
    "ну ти там держись": "Ссикло",
    "а воно мені не нада": "не мужик",
    "наш живчик": "містер біст",
    "сігма бой": "Богдан"
}

# Для антиспаму
user_messages = defaultdict(list)
banned_users = {}

# Для підрахунку фраз
message_count = 0

# Параметри обмежень
SPAM_LIMIT = 150
TIME_WINDOW = 5 * 60
BAN_TIME = 15 * 60

# Функція нормалізації тексту
def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)  # видалити емодзі та символи
    return text.strip()

# Пошук схожої фрази
def is_similar(input_text):
    for phrase in PHRASES:
        ratio = SequenceMatcher(None, input_text, phrase).ratio()
        if ratio > 0.7:
            return True
    return False

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я ржомба бот")

# /words
async def words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word_list = "\n".join([f"- {w}" for w in PHRASES])
    await update.message.reply_text(f"Ось фрази, які я розумію:\n{word_list}")

# Основна логіка
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global message_count
    user_id = update.effective_user.id
    now = datetime.now()
    user_message = update.message.text.strip()

    # Перевірка бану
    if user_id in banned_users:
        if now < banned_users[user_id]:
            await update.message.reply_text("Ти в бані, почекай 15 хвилин.")
            return
        else:
            del banned_users[user_id]

    # Спам контроль
    user_messages[user_id].append(now)
    user_messages[user_id] = [t for t in user_messages[user_id] if (now - t).total_seconds() <= TIME_WINDOW]
    if len(user_messages[user_id]) > SPAM_LIMIT:
        banned_users[user_id] = now + timedelta(seconds=BAN_TIME)
        await update.message.reply_text("Не дрочи так часто - хуй болітиме")
        return

    # Обробка повідомлення
    norm_msg = normalize(user_message)
    if norm_msg in PHRASES:
        await update.message.reply_text(PHRASES[norm_msg])
        message_count += 1
    elif is_similar(norm_msg):
        await update.message.reply_text("Ти мазила")
    else:
        await update.message.reply_text("Ржомба")
        return  # не рахуємо в message_count

    if message_count >= 5:
        await update.message.reply_text("Ржомба")
        message_count = 0

# Запуск
app = ApplicationBuilder().token("7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("words", words))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
app.run_polling()
