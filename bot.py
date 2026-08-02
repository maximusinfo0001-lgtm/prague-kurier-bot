import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
import asyncio
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
TURSO_URL = os.getenv("TURSO_URL")
TURSO_TOKEN = os.getenv("TURSO_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def execute_sql(sql, params=None):
    """Выполнить SQL через HTTP API Turso"""
    url = TURSO_URL.replace("libsql://", "https://") + "/v2"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    # Формируем SQL с подставленными параметрами
    if params:
        for p in params:
            if isinstance(p, str):
                escaped = p.replace("'", "''")
                sql = sql.replace("?", f"'{escaped}'", 1)
            else:
                sql = sql.replace("?", str(p), 1)
    
    data = {"statements": [sql]}
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


def init_db():
    url = TURSO_URL.replace("libsql://", "https://") + "/v2"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"statements": ["CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT, note TEXT, created_at TEXT, updated_at TEXT)"]}
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    print("init_db:", resp.json())


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.reply(
        "👋 **Pražský kurýr** — databáze zkušeností doručovatelů.\n\n"
        "/add Adresa poznámka — přidat\n"
        "/get Adresa — zobrazit\n"
        "/fix Adresa staré nové — opravit\n"
        "/help — nápověda"
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.reply(
        "📋 **Příkazy:**\n\n"
        "➕ /add Adresa poznámka\n"
        "🔍 /get Adresa\n"
        "✏️ /fix Adresa staré nové"
    )


@dp.message(Command("add"))
async def add_note(message: types.Message):
    text = message.text.replace("/add", "").strip()
    parts = text.split(" ", 2)
    if len(parts) < 3:
        await message.reply("❌ Formát: /add Ulice číslo poznámka")
        return
    address = (parts[0] + " " + parts[1]).lower().strip()
    note = parts[2].strip()
    now = datetime.now().isoformat()
    execute_sql(
        "INSERT INTO notes (address, note, created_at, updated_at) VALUES (?, ?, ?, ?)",
        [address, note, now, now]
    )
    await message.reply(f"✅ Zapsáno: {address} → {note}")


@dp.message(Command("get"))
async def get_notes(message: types.Message):
    address = message.text.replace("/get", "").strip().lower()
    if not address:
        await message.reply("❌ Formát: /get Ulice číslo")
        return
    result = execute_sql(
        "SELECT note, updated_at FROM notes WHERE address = ? ORDER BY updated_at DESC LIMIT 10",
        [address]
    )
    rows = result["results"][0]["rows"]
    if not rows:
        await message.reply(f"📍 {address}\n\nZatím žádné poznámky.\nBuďte první: /add {address} vaše_poznámka")
        return
    response = f"📍 {address}\n\n"
    for row in rows:
        note = row[0]["value"]
        updated = row[1]["value"]
        try:
            days_ago = (datetime.now() - datetime.fromisoformat(updated)).days
            time_text = "dnes" if days_ago == 0 else "včera" if days_ago == 1 else f"před {days_ago} dny"
        except Exception:
            time_text = "datum neznámé"
        response += f"• {note} ({time_text})\n"
    await message.reply(response)


@dp.message(Command("fix"))
async def fix_note(message: types.Message):
    text = message.text.replace("/fix", "").strip()
    parts = text.split(" ", 2)
    if len(parts) < 3:
        await message.reply("❌ Formát: /fix Ulice číslo staré nové")
        return
    address = (parts[0] + " " + parts[1]).lower().strip()
    old_part = parts[2].split(" ")[0].strip()
    new_part = " ".join(parts[2].split(" ")[1:]).strip()
    now = datetime.now().isoformat()
    result = execute_sql(
        "UPDATE notes SET note = ?, updated_at = ? WHERE address = ? AND note LIKE ?",
        [new_part, now, address, f"%{old_part}%"]
    )
    updated = result["results"][0]["rows_affected"]
    if updated:
        await message.reply(f"✅ Aktualizováno: {old_part} → {new_part}")
    else:
        await message.reply(f"❌ Nenalezeno: '{old_part}' pro {address}")


@dp.message()
async def any_message(message: types.Message):
    await message.reply("Rozumím jen příkazům. /help pro seznam.")


async def main():
    init_db()
    asyncio.create_task(dp.start_polling(bot))
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    print("Bot + HTTP server running on port 10000...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
