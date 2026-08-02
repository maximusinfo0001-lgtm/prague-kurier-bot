import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
import asyncio
import requests
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
TURSO_URL = os.getenv("TURSO_URL")
TURSO_TOKEN = os.getenv("TURSO_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def execute_sql(sql, params=None):
    url = TURSO_URL.replace("libsql://", "https://") + "/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    args = []
    if params:
        for p in params:
            if isinstance(p, str):
                args.append({"type": "text", "value": p})
            else:
                args.append({"type": "text", "value": str(p)})
    data = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": args}}
        ]
    }
    resp = requests.post(url, headers=headers, json=data)
    return resp


def init_db():
    resp = execute_sql("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT, note TEXT, created_at TEXT, updated_at TEXT)")
    print("init_db status:", resp.status_code)
    print("init_db body:", resp.text)


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
    resp = execute_sql(
        "INSERT INTO notes (address, note, created_at, updated_at) VALUES (?, ?, ?, ?)",
        [address, note, now, now]
    )
    await message.reply(f"✅ Zapsáno: {address} → {note}\nStatus: {resp.status_code}")


@dp.message(Command("get"))
async def get_notes(message: types.Message):
    address = message.text.replace("/get", "").strip().lower()
    if not address:
        await message.reply("❌ Formát: /get Ulice číslo")
        return
    resp = execute_sql(
        "SELECT note, updated_at FROM notes WHERE address = ? ORDER BY updated_at DESC LIMIT 10",
        [address]
    )
    await message.reply(f"DEBUG status: {resp.status_code}\nDEBUG body: {resp.text[:500]}")


@dp.message(Command("fix"))
async def fix_note(message: types.Message):
    await message.reply("Funkce /fix dočasně nedostupná.")


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
