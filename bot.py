import os
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
from difflib import SequenceMatcher
TOKEN = "7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig"
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from aiohttp import web
import asyncio

# ======= Налаштування =======
OWNER_ID = 1234960363
PORT = int(os.getenv("PORT", "8080"))
TOKEN = os.getenv("7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig")

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
energy_max = 100
energy_recover_period = 5
events_days = {0, 2, 3, 4}
daily_base = 50

DATA_FILE = "users.json"
DAILY_FILE = "daily.json"

# ======= Зберігання =======
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default

profiles = load_json(DATA_FILE, {})
daily = load_json(DAILY_FILE, {})
banned_users = {}
ban_counts = defaultdict(int)
user_messages = defaultdict(list)

async def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(profiles, f)
    with open(DAILY_FILE, "w") as f:
        json.dump(daily, f)

# ======= Допоміжні =======
def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def similar(text):
    for phrase in PHRASES:
        if SequenceMatcher(None, text, phrase).ratio() > 0.7:
            return True
    return False

def fmt(text):
    return " ".join(w.capitalize() for w in text.split())

def parse_time(arg):
    unit = arg[-1]
    num = int(arg[:-1])
    return {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}.get(unit, 1800) * num

# ======= Команди =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я Ржомба Бот 🤖")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = ["/start", "/help", "/profile", "/daily"]
    await update.message.reply_text("Команди:\n" + "\n".join(commands))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    p = profiles.get(uid, {})
    text = f"@{p.get('username', 'немає')}\nМонети: {p.get('coins', 0)}\nРжомба: {p.get('rzhomb', 0)}"
    await update.message.reply_text(text)

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    now = int(datetime.now().timestamp())
    last = daily.get(uid, 0)
    if now - last < 86400:
        await update.message.reply_text("Сьогодні ти вже отримував.")
        return
    award = daily_base
    profiles.setdefault(uid, {}).setdefault("coins", 0)
    profiles[uid]["coins"] += award
    daily[uid] = now
    await save_data()
    await update.message.reply_text(f"Тримай {award} монет!")

# ======= Повідомлення =======
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    uid = update.effective_user.id
    uname = update.effective_user.username or f"user{uid}"
    text = update.message.text or ""
    profile = profiles.setdefault(str(uid), {
        "username": uname, "rzhomb": 0, "coins": 0, "energy": energy_max, "energy_last_update": now.timestamp()
    })

    # Energy recovery
    last = datetime.fromtimestamp(profile['energy_last_update'])
    recovered = (now - last).seconds // (energy_recover_period * 60)
    if recovered > 0:
        profile['energy'] = min(energy_max, profile['energy'] + recovered)
        profile['energy_last_update'] = now.timestamp()

    # Спам-фільтр
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if (now - t).seconds < TIME_WINDOW]
    if len(user_messages[uid]) > SPAM_LIMIT:
        return

    # Обробка
    norm = normalize(text)
    cnt = text.lower().count("ржомба")
    if cnt > 0 and profile["energy"] >= cnt:
        profile["rzhomb"] += cnt
        profile["coins"] += cnt * 2
        profile["energy"] -= cnt
        await update.message.reply_text(f"Ржомба! +{cnt*2} монет")
    elif norm in PHRASES:
        await update.message.reply_text(PHRASES[norm])
    elif similar(norm):
        await update.message.reply_text("Ти мазила")
    else:
        await update.message.reply_text("Ржомба")

    await save_data()

# ======= Запуск через вебхук =======
async def run():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    async def handler(request):
        data = await request.json()
        await app.update_queue.put(Update.de_json(data, app.bot))
        return web.Response()

    webhook_app = web.Application()
    webhook_app.add_routes([web.post("/", handler)])
    await app.initialize()
    await app.bot.set_webhook(f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'your-render-url')}/")
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Bot running on port {PORT}")

    # Keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run())
