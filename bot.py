import random
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# === Налаштування ===
YOUR_ID = 1234960363  # твій Telegram user ID

# Словник фраз (що має написати користувач)
PHRASES = {
    "ржомба": "🤣",
    "ну ти там держись": "ССИКЛО",
    "а воно мені не нада": "НЕ МУЖИК",
    "наш живчик": "МІСТЕР БІСТ",
    "сігма бой": "БОГДАН"
}

# Антиспам
user_messages = defaultdict(list)
banned_users = {}
user_ban_durations = defaultdict(lambda: 5 * 60)  # перший бан — 5 хв
message_count = 0

SPAM_LIMIT = 150
TIME_WINDOW = 5 * 60
MAX_BAN = 30 * 60

# Нормалізація тексту
def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()

# Перевірка на схожість
def is_similar(input_text):
    for phrase in PHRASES:
        ratio = SequenceMatcher(None, input_text, phrase).ratio()
        if ratio > 0.7:
            return True
    return False

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я РЖОМБА БОТ")

# /words
async def words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word_list = "\n".join([f"- {w.upper()}" for w in PHRASES])
    await update.message.reply_text(f"ОСЬ ФРАЗИ, ЯКІ Я РОЗУМІЮ:\n{word_list}")

# /banlist
async def banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not banned_users:
        await update.message.reply_text("ЗАРАЗ НІКОГО НЕ ЗАБАНЕНО.")
        return
    text = "ЗАБАНЕНІ КОРИСТУВАЧІ:\n"
    for uid, end_time in banned_users.items():
        until = end_time.strftime("%H:%M %d.%m.%Y")
        text += f"• ID {uid} — ДО {until}\n"
    await update.message.reply_text(text.strip())

# /unban <user_id>
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != YOUR_ID:
        return
    if not context.args:
        await update.message.reply_text("ВКАЖИ ID КОРИСТУВАЧА")
        return
    try:
        uid = int(context.args[0])
        if uid in banned_users:
            del banned_users[uid]
            user_ban_durations[uid] = 5 * 60
            await update.message.reply_text(f"КОРИСТУВАЧ {uid} РОЗБЛОКОВАНИЙ.")
        else:
            await update.message.reply_text("КОРИСТУВАЧ НЕ В БАНІ.")
    except ValueError:
        await update.message.reply_text("НЕКОРЕКТНИЙ ID.")

# Обробка повідомлень
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global message_count
    user_id = update.effective_user.id
    now = datetime.now()
    user_message = update.message.text.strip()

    # Бан
    if user_id in banned_users:
        if now < banned_users[user_id]:
            return  # нічого не відповідаємо
        else:
            del banned_users[user_id]

    # Спам
    user_messages[user_id].append(now)
    user_messages[user_id] = [t for t in user_messages[user_id] if (now - t).total_seconds() <= TIME_WINDOW]
    if len(user_messages[user_id]) > SPAM_LIMIT:
        duration = user_ban_durations[user_id]
        banned_users[user_id] = now + timedelta(seconds=duration)
        user_ban_durations[user_id] = min(duration + 5 * 60, MAX_BAN)
        return

    norm_msg = normalize(user_message)
    if norm_msg in PHRASES:
        await update.message.reply_text(PHRASES[norm_msg])
        message_count += 1
    elif is_similar(norm_msg):
        await update.message.reply_text("ТИ МАЗИЛА")
        message_count += 1
    else:
        await update.message.reply_text("РЖОМБА")
        return

    if message_count >= 5:
        await update.message.reply_text("РЖОМБА")
        message_count = 0

# Запуск
app = ApplicationBuilder().token("7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("words", words))
app.add_handler(CommandHandler("banlist", banlist))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
app.run_polling()
