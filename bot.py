import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
import asyncio
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = "prague_kurier_notes.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT,
            note TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.reply(
        "👋 **Pražský kurýr** — databáze zkušeností doručovatelů.\n\n"
        "Zde najdete tipy k adresám v Praze:\n"
        "kde je vchod, kód domofonu, kde je box v OC.\n\n"
        "Příkazy:\n"
        "/add Adresa poznámka — přidat\n"
        "/get Adresa — zobrazit\n"
        "/fix Adresa staré nové — opravit\n"
        "/help — nápověda"
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.reply(
        "📋 **Příkazy Pražského kurýra**\n\n"
        "➕ /add Adresa poznámka\n"
        "Příklad: /add Vinohradska 15 kod 1234\n\n"
        "🔍 /get Adresa\n"
        "Příklad: /get Vinohradska 15\n\n"
        "✏️ /fix Adresa staré nové\n"
        "Příklad: /fix Vinohradska 15 kod 5678"
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO notes (address, note, created_at, updated_at) VALUES (?, ?, ?, ?)",
              (address, note, now, now))
    conn.commit()
    conn.close()
    await message.reply(f"✅ Zapsáno: {address} → {note}")


@dp.message(Command("get"))
async def get_notes(message: types.Message):
    address = message.text.replace("/get", "").strip().lower()
    if not address:
        await message.reply("❌ Formát: /get Ulice číslo")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT note, updated_at FROM notes WHERE address = ? ORDER BY updated_at DESC LIMIT 10", (address,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await message.reply(f"📍 {address}\n\nZatím žádné poznámky.\nBuďte první: /add {address} vaše_poznámka")
        return
    response = f"📍 {address}\n\n"
    for note, updated in rows:
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE notes SET note = ?, updated_at = ? WHERE address = ? AND note LIKE ?",
              (new_part, now, address, f"%{old_part}%"))
    updated = c.rowcount
    conn.commit()
    conn.close()
    if updated:
        await message.reply(f"✅ Aktualizováno: {old_part} → {new_part}")
    else:
        await message.reply(f"❌ Nenalezeno: '{old_part}' pro {address}")


@dp.message()
async def any_message(message: types.Message):
    await message.reply("Rozumím jen příkazům. /help pro seznam.")


async def main():
    init_db()
    # Spustíme bota na pozadí
    asyncio.create_task(dp.start_polling(bot))
    # HTTP server aby Render nezabil službu
    app = web.Application()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    print("Bot + HTTP server running on port 10000...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
