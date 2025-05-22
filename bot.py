import os
import json
import re
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import asyncio

# ======= Налаштування =======
OWNER_ID = 1234960363
TOKEN = "7957837080:AAH1O_tEfW9xC9jfUt2hRXILG-Z579_w7ig"  # Встав сюди свій токен

PHRASES = {
    "ржомба": "🤣",
    "ну ти там держись": "😏 Ссикло",
    "а воно мені не нада": "🙅‍♂️ Не мужик",
    "наш живчик": "🔥 Містер Біст",
    "сігма бой": "💪 Богдан",
}

SPAM_LIMIT = 150
TIME_WINDOW = 300
energy_max = 100
energy_recover_period = 5
daily_base = 50

DATA_FILE = "users.json"
DAILY_FILE = "daily.json"

# ======= Зберігання =======
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

profiles = load_json(DATA_FILE, {})
daily = load_json(DAILY_FILE, {})
user_messages = defaultdict(list)

async def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    with open(DAILY_FILE, "w", encoding="utf-8") as f:
        json.dump(daily, f, ensure_ascii=False, indent=2)

# ======= Допоміжні =======
def normalize(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()

def similar(text):
    for phrase in PHRASES:
        if SequenceMatcher(None, text, phrase).ratio() > 0.7:
            return True
    return False

# ======= Команди =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Привіт! Я — Ржомба Бот, твій веселий помічник!")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands = [
        "/start — Запуск бота",
        "/help — Допомога",
        "/profile — Твій профіль",
        "/daily — Щоденна нагорода",
        "/words — Список моїх слів",
        "/smileys — Смайлики та фрази",
        "/duel @user — Виклик на дуель",
        "/accept_duel — Прийняти дуель",
        "/setphoto — Додати фото в профіль (надішли фото з командою)",
    ]
    await update.message.reply_text("🛠️ Команди:\n" + "\n".join(commands))

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    p = profiles.get(uid, {
        "username": update.effective_user.username or f"user{uid}",
        "favorite_phrase": "Ржомба",
        "rzhomb": 0,
        "coins": 0,
        "bans": 0,
        "photo_id": None,
    })

    text = (
        f"👤 Профіль: @{p.get('username', 'немає')}\n"
        f"💬 Улюблена фраза: «{p.get('favorite_phrase', 'Ржомба')}»\n"
        f"📊 Ржомбометр: {p.get('rzhomb', 0)} 🔥\n"
        f"🪙 Монети: {p.get('coins', 0)} 💰\n"
        f"🚫 Забанений разів: {p.get('bans', 0)} ❌"
    )

    if p.get("photo_id"):
        await update.message.reply_photo(photo=p["photo_id"], caption=text)
    else:
        await update.message.reply_text(text)

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    now = int(datetime.now().timestamp())
    last = daily.get(uid, 0)
    if now - last < 86400:
        await update.message.reply_text("⏳ Сьогодні ти вже отримував свою нагороду.")
        return
    award = daily_base
    profiles.setdefault(uid, {}).setdefault("coins", 0)
    profiles[uid]["coins"] += award
    daily[uid] = now
    await save_data()
    await update.message.reply_text(f"🎉 Тримай {award} монет!")

async def words_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Слова, які я знаю:\n" + ", ".join(PHRASES.keys()))

# ======= Повідомлення =======
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    uid = update.effective_user.id
    uname = update.effective_user.username or f"user{uid}"
    text = update.message.text or ""
    profile = profiles.setdefault(str(uid), {
        "username": uname,
        "favorite_phrase": "Ржомба",
        "rzhomb": 0,
        "coins": 0,
        "energy": energy_max,
        "energy_last_update": now.timestamp(),
        "bans": 0,
        "photo_id": None,
    })

    # Відновлення енергії
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

    # Обробка повідомлень
    norm = normalize(text)
    cnt = text.lower().count("ржомба")
    if cnt > 0 and profile["energy"] >= cnt:
        profile["rzhomb"] += cnt
        profile["coins"] += cnt * 2
        profile["energy"] -= cnt
        await update.message.reply_text(f"🤣 Ржомба! +{cnt*2} монет 🪙")
    elif norm in PHRASES:
        await update.message.reply_text(f"{PHRASES[norm]}")
    elif similar(norm):
        await update.message.reply_text("🤡 Ти мазила!")
    else:
        await update.message.reply_text("😂 Ржомба!")

    await save_data()

# ======= Додаткова команда для встановлення фото =======
async def setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if not update.message.photo:
        await update.message.reply_text("📸 Будь ласка, надішли фото разом із командою /setphoto")
        return
    photo = update.message.photo[-1]  # Найвища якість
    profiles.setdefault(uid, {}).update({"photo_id": photo.file_id})
    await save_data()
    await update.message.reply_text("✅ Фото успішно додано в профіль!")

# ======= Запуск бота =======
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("words", words_cmd))
    app.add_handler(CommandHandler("setphoto", setphoto))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
