import random
import re
import json
import os
import threading
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

PHRASES = {
    "ржомба": "🤣",
    "ну ти там держись": "Ссикло",
    "а воно мені не нада": "Не мужик",
    "наш живчик": "Містер Біст",
    "сігма бой": "Богдан",
}

SPAM_LIMIT = 150
BAN_STEPS = [300, 600, 900, 1800]
TIME_WINDOW = 300
DATA_FILE = "users.json"

user_messages = defaultdict(list)
banned_users = {}
ban_counts = defaultdict(int)
profiles = {}
OWNER_ID = 1234960363  # заміни на свій ID

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        profiles = json.load(f)

async def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(profiles, f)

def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def similar(input_text):
    for phrase in PHRASES:
        ratio = SequenceMatcher(None, input_text, phrase).ratio()
        if ratio > 0.7:
            return True
    return False

def fmt(text):
    return " ".join(w.capitalize() for w in text.split())

def parse_time(arg):
    if arg.endswith("s"):
        return int(arg[:-1])
    elif arg.endswith("m"):
        return int(arg[:-1]) * 60
    elif arg.endswith("h"):
        return int(arg[:-1]) * 3600
    elif arg.endswith("d"):
        return int(arg[:-1]) * 86400
    return 1800

# --- КОМАНДИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я Ржомба Бот 🤖")

async def words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 Фрази: \n" + "\n".join(["- " + fmt(w) for w in PHRASES]))

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args or not context.args[0].startswith("@"):
        return
    username = context.args[0][1:]
    duration = parse_time(context.args[1]) if len(context.args) > 1 else 1800
    for uid, profile in profiles.items():
        if profile.get("username") == username:
            banned_users[int(uid)] = datetime.now() + timedelta(seconds=duration)
            await update.message.reply_text(f"🚫 @{username} забанено на {duration // 60} хв.")
            return
    await update.message.reply_text("❌ Користувача не знайдено.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args or not context.args[0].startswith("@"):
        return
    username = context.args[0][1:]
    for uid in list(banned_users):
        if profiles.get(str(uid), {}).get("username") == username:
            del banned_users[uid]
            await update.message.reply_text(f"✅ Користувача @{username} розбанено.")
            return
    await update.message.reply_text("❌ Користувача не знайдено або не забанений.")

async def banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    lst = [f"@{profiles[str(uid)].get('username')}" for uid in banned_users if str(uid) in profiles]
    await update.message.reply_text("🚷 Забанені: \n" + "\n".join(lst) if lst else "Немає забанених")

async def setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        profiles.setdefault(uid, {})
        profiles[uid]["photo"] = file_id
        await save_data()
        await update.message.reply_text("🖼 Фото встановлено!")
    else:
        await update.message.reply_text("📷 Пришли фото, яке хочеш встановити у профіль")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data = profiles.get(uid, {})
    text = f"👤 Профіль @{data.get('username', 'немає')}\n"
    text += f"💬 Улюблена фраза: {fmt(data.get('fav', 'Немає'))}\n"
    text += f"📊 Ржомбометр: {data.get('rzhomb', 0)}\n"
    text += f"🪙 Монети: {data.get('coins', 0)}\n"
    text += f"🚫 Забанений разів: {data.get('bans', 0)}"
    if data.get("photo"):
        await update.message.reply_photo(data["photo"], caption=text)
    else:
        await update.message.reply_text(text)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_list = sorted(profiles.items(), key=lambda x: (-x[1].get("coins", 0), -x[1].get("rzhomb", 0)))[:10]
    text = "🏆 Таблиця лідерів:\n"
    for uid, data in top_list:
        text += f"@{data.get('username', 'немає')} — {data.get('coins', 0)} монет, {data.get('rzhomb', 0)} ржомб\n"
    await update.message.reply_text(text)

# --- ГОЛОВНА ЛОГІКА ---

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    uid = update.effective_user.id
    username = update.effective_user.username or f"user{uid}"
    profiles.setdefault(str(uid), {}).update({"username": username})
    profiles[str(uid)].setdefault("rzhomb", 0)
    profiles[str(uid)].setdefault("coins", 0)
    profiles[str(uid)].setdefault("bans", 0)

    if uid in banned_users and now < banned_users[uid]:
        return

    text = normalize(update.message.text)
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if (now - t).total_seconds() < TIME_WINDOW]

    if len(user_messages[uid]) > SPAM_LIMIT:
        ban_count = ban_counts[uid]
        duration = BAN_STEPS[min(ban_count, len(BAN_STEPS) - 1)]
        banned_users[uid] = now + timedelta(seconds=duration)
        ban_counts[uid] += 1
        profiles[str(uid)]["bans"] += 1
        await save_data()
        return

    if "богдан" in text:
        await update.message.reply_text("Я Кінчив")
    elif text in PHRASES:
        profiles[str(uid)]["rzhomb"] += 1
        profiles[str(uid)]["coins"] += 1
        fav = profiles[str(uid)].get("fav")
        if not fav:
            profiles[str(uid)]["fav"] = text
        await update.message.reply_text(fmt(PHRASES[text]))
    elif similar(text):
        await update.message.reply_text("Ти Мазила")
    else:
        await update.message.reply_text("Ржомба")

    await save_data()

# --- ФОН ДЛЯ ПІДТРИМКИ АКТИВНОСТІ ---

def keep_alive():
    async def loop():
        while True:
            await asyncio.sleep(60)
    asyncio.run(loop())

# --- MAIN ---

def main():
    app = ApplicationBuilder().token("7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("words", words))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("banlist", banlist))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("setphoto", setphoto))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    app.add_handler(MessageHandler(filters.PHOTO, setphoto))

    threading.Thread(target=keep_alive, daemon=True).start()
    app.run_polling()

if __name__ == "__main__":
    main()
