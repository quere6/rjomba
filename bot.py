import random
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from collections import defaultdict
from datetime import datetime, timedelta

# Словник фраз і відповідей
RESPONSES = {
    "Ржомба": "🤣",
    "Ну ти там держись ✊": "Ссикло",
    "А воно мені не нада": "не мужик",
    "Наш Живчик 🇺🇦🇺🇦🇺🇦": "містер біст"
}

phrase_count = 0  # Лічильник фраз, що співпали

# Для спам-захисту
user_messages = defaultdict(list)
banned_users = {}

SPAM_LIMIT = 150       # повідомлень
TIME_WINDOW = 5 * 60   # 5 хвилин (секунди)
BAN_TIME = 15 * 60     # 15 хвилин (секунди)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global phrase_count
    user_id = update.effective_user.id
    now = datetime.now()
    user_message = update.message.text.strip()

    # Перевірка бану
    if user_id in banned_users:
        ban_end = banned_users[user_id]
        if now < ban_end:
            await update.message.reply_text("Ти в бані, почекай 15 хвилин.")
            return
        else:
            del banned_users[user_id]

    # Оновлення часу повідомлень користувача
    user_messages[user_id].append(now)
    # Очищуємо старі повідомлення за межами 5 хвилин
    user_messages[user_id] = [t for t in user_messages[user_id] if (now - t).total_seconds() <= TIME_WINDOW]

    # Перевірка на спам
    if len(user_messages[user_id]) > SPAM_LIMIT:
        banned_users[user_id] = now + timedelta(seconds=BAN_TIME)
        await update.message.reply_text("Не дрочи так часто - хуй болітиме")
        return

    # Якщо повідомлення співпало з однією із фраз
    if user_message in RESPONSES:
        phrase_count += 1
        await update.message.reply_text(RESPONSES[user_message])

        # Після 5 фраз – бот пише "Ржомба"
        if phrase_count >= 5:
            await update.message.reply_text("Ржомба")
            phrase_count = 0
    else:
        # Повідомлення не співпало з фразою – відразу відповідаємо "Ржомба" і не рахуємо у phrase_count
        await update.message.reply_text("Ржомба")

app = ApplicationBuilder().token("7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig").build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
app.run_polling()
