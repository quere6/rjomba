import random
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

RESPONSES = {
    "Ржомба": "🤣",
    "Ну ти там держись ✊": "Ссикло",
    "А воно мені не нада": "не мужик",
    "Наш Живчик 🇺🇦🇺🇦🇺🇦": "містер біст"
}

message_count = 0

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global message_count
    user_message = update.message.text.strip()
    message_count += 1

    # Відповідь на відомі фрази
    if user_message in RESPONSES:
        await update.message.reply_text(RESPONSES[user_message])
    elif message_count >= 5:
        await update.message.reply_text("Ржомба")
        message_count = 0

app = ApplicationBuilder().token("7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig").build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
app.run_polling()
