import random
import re
import json
import os
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
DAILY_FILE = "daily.json"

OWNER_ID = 1234960363

energy_max = 100
energy_recover_period = 5

events_days = {0, 2, 3, 4}
daily_base = 50

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

def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def similar(input_text):
    for phrase in PHRASES:
        if SequenceMatcher(None, input_text, phrase).ratio() > 0.7:
            return True
    return False

def fmt(text):
    return " ".join(w.capitalize() for w in text.split())

def parse_time(arg):
    unit = arg[-1]
    num = int(arg[:-1])
    return {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}.get(unit, 1800) * num

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я Ржомба Бот 🤖. Використай /help для списку команд.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start", "/help", "/words", "/ban @user [time]", "/unban @user", "/banlist",
        "/profile", "/setphoto", "/top", "/daily", "/duel @user"
    ]
    await update.message.reply_text("Доступні команди:\n" + "\n".join(commands))

async def words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\ud83d\udcda Фрази: \n" + "\n".join(["- " + fmt(w) for w in PHRASES]))

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args or not context.args[0].startswith("@"): 
        return
    user, duration = context.args[0][1:], parse_time(context.args[1]) if len(context.args) > 1 else 1800
    for uid, p in profiles.items():
        if p.get('username') == user:
            banned_users[int(uid)] = datetime.now() + timedelta(seconds=duration)
            await update.message.reply_text(f"\ud83d\udeab @{user} забанено на {duration//60} хв.")
            return
    await update.message.reply_text("\u274c Користувача не знайдено.")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args or not context.args[0].startswith("@"): 
        return
    user = context.args[0][1:]
    for uid in list(banned_users):
        if profiles.get(str(uid), {}).get('username') == user:
            del banned_users[uid]
            await update.message.reply_text(f"\u2705 @{user} розбанено.")
            return
    await update.message.reply_text("\u274c Не знайдено.")

async def banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    lst = [f"@{profiles[str(uid)]['username']}" for uid in banned_users if str(uid) in profiles]
    await update.message.reply_text("\ud83d\ude37 Забанені:\n" + ("\n".join(lst) if lst else "немає"))

async def setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if update.message.photo:
        profiles.setdefault(uid, {})['photo'] = update.message.photo[-1].file_id
        await save_data()
        await update.message.reply_text("\ud83d\uddbc Фото встановлено!")
    else:
        await update.message.reply_text("\ud83d\udcf7 Надішли фото без команди.")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    p = profiles.get(uid, {})
    txt = f"\ud83d\udc64 Профіль @{p.get('username', 'немає')}\n"
    txt += f"\ud83d\udcca Ржомбометр: {p.get('rzhomb', 0)}\n"
    txt += f"\ud83e\ude99 Монети: {p.get('coins', 0)}\n"
    txt += f"\u26a1 Енергія: {p.get('energy', 0)}\n"
    txt += f"\ud83d\udd1d Рівень: {p.get('level', 'Новачок')}"
    if p.get('photo'):
        await update.message.reply_photo(p['photo'], caption=txt)
    else:
        await update.message.reply_text(txt)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arr = sorted(profiles.items(), key=lambda x: (-x[1].get('coins', 0), -x[1].get('rzhomb', 0)))[:10]
    msg = "\ud83c\udfc6 Лідери:\n"
    for uid, p in arr:
        msg += f"@{p.get('username', '')} {p.get('coins', 0)}\ud83d\udcb0 {p.get('rzhomb', 0)}\ud83e\udd23\n"
    await update.message.reply_text(msg)

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    now = int(datetime.now().timestamp())
    last = daily.get(uid, 0)
    if now - last < 86400:
        await update.message.reply_text("\u23f3 Завтра буде нова нагорода.")
        return
    base = daily_base
    bal = profiles.setdefault(uid, {}).get('coins', 0)
    award = base if last == 0 else base + int(bal * 0.15)
    profiles[uid]['coins'] = bal + award
    daily[uid] = now
    await save_data()
    await update.message.reply_text(f"\ud83c\udf81 Отримано {award} монет!")

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\u2694\ufe0f Дуелі ще в розробці...")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    uid = update.effective_user.id
    txt_raw = update.message.text or ''
    uname = update.effective_user.username or f'user{uid}'
    p = profiles.setdefault(str(uid), {'username': uname, 'rzhomb': 0, 'coins': 0, 'energy': energy_max, 'bans': 0, 'energy_last_update': now.timestamp(), 'level': 'Новачок'})

    last = datetime.fromtimestamp(p['energy_last_update'])
    rec = (now - last).seconds // (energy_recover_period * 60)
    if rec > 0:
        p['energy'] = min(energy_max, p['energy'] + rec)
        p['energy_last_update'] = now.timestamp()

    if uid in banned_users and now < banned_users[uid]:
        return

    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if (now - t).seconds < TIME_WINDOW]
    if len(user_messages[uid]) > SPAM_LIMIT:
        c = ban_counts[uid]
        d = BAN_STEPS[min(c, len(BAN_STEPS) - 1)]
        banned_users[uid] = now + timedelta(seconds=d)
        ban_counts[uid] += 1
        p['bans'] += 1
        await save_data()
        return

    cnt = txt_raw.lower().count('ржомба')
    mult = 2 if datetime.today().weekday() in events_days else 1

    if cnt > 0:
        cost = cnt
        if p['energy'] >= cost:
            earned = cnt * mult
            p['rzhomb'] += cnt
            p['coins'] += earned
            p['energy'] -= cost
            total_msgs = len(user_messages[uid])
            if total_msgs > 500:
                p['level'] = 'Майстер Ржомби'
            elif total_msgs > 100:
                p['level'] = 'Просунутий'
            elif total_msgs > 30:
                p['level'] = 'Любитель'
            await update.message.reply_text(f"Зароблено {earned} монет! Енергія: {p['energy']}. Рівень: {p['level']}")
        else:
            await update.message.reply_text(f"Не вистачає енергії ({p['energy']})")
    elif 'богдан' in txt_raw.lower():
        await update.message.reply_text('Я Кінчив')
    elif normalize(txt_raw) in PHRASES:
        await update.message.reply_text(fmt(PHRASES[normalize(txt_raw)]))
    elif similar(normalize(txt_raw)):
        await update.message.reply_text('Ти Мазила')
    else:
        await update.message.reply_text('Ржомба')
    await save_data()

async def background_task():
    while True:
        await asyncio.sleep(60)

async def main():
    app = ApplicationBuilder().token("YOUR_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("words", words))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("banlist", banlist))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("setphoto", setphoto))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("duel", duel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    app.add_handler(MessageHandler(filters.PHOTO, setphoto))

    asyncio.create_task(background_task())
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
