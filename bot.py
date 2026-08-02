import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
from datetime import datetime

# ============================================
# НАСТРОЙКИ
# ============================================
BOT_TOKEN = "8966293113:AAHV5ovVyjOxF2wDgvo3D4JFF7z7oI0QFAg"

# ============================================
DB_PATH = "/home/praguekurier/prague_kurier_notes.db"

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
        "👋 **Пражский курьер** — база опыта доставщиков.\n\n"
        "Здесь собраны подсказки по адресам Праги:\n"
        "где вход, какой код домофона, где постамат в ТЦ.\n\n"
        "Команды:\n"
        "/add Адрес заметка — добавить\n"
        "/get Адрес — посмотреть\n"
        "/fix Адрес старое новое — исправить\n"
        "/help — помощь\n\n"
        "Начните с /get и адреса, который знаете."
    )


@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.reply(
        "📋 **Команды Пражского курьера**\n\n"
        "➕ **/add Адрес заметка**\n"
        "Добавить подсказку\n"
        "Пример: /add Vinohradska 15 kod 1234\n\n"
        "🔍 **/get Адрес**\n"
        "Показать все подсказки\n"
        "Пример: /get Vinohradska 15\n\n"
        "✏️ **/fix Адрес старое новое**\n"
        "Исправить заметку\n"
        "Пример: /fix Vinohradska 15 kod 5678\n\n"
        "💡 Адрес пишите так: улица и номер дома.\n"
        "Ulice a číslo popisné: Vinohradska 15\n\n"
        "Čím více poznámek, tím rychlejší doručení."
    )


@dp.message(Command("add"))
async def add_note(message: types.Message):
    text = message.text.replace("/add", "").strip()
    parts = text.split(" ", 2)

    if len(parts) < 3:
        await message.reply(
            "❌ Špatný formát.\n\n"
            "Správně: /add Ulice číslo poznámka\n"
            "Příklad: /add Vinohradska 15 vchod ze dvora"
        )
        return

    address = (parts[0] + " " + parts[1]).lower().strip()
    note = parts[2].strip()
    now = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO notes (address, note, created_at, updated_at) "
        "VALUES (?, ?, ?, ?)",
        (address, note, now, now)
    )
    conn.commit()
    conn.close()

    await message.reply(f"✅ Zapsáno: {address} → {note}")


@dp.message(Command("get"))
async def get_notes(message: types.Message):
    address = message.text.replace("/get", "").strip().lower()

    if not address:
        await message.reply(
            "❌ Zadejte adresu.\n\n"
            "Formát: /get Ulice číslo\n"
            "Příklad: /get Vinohradska 15"
        )
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT note, updated_at FROM notes "
        "WHERE address = ? ORDER BY updated_at DESC LIMIT 10",
        (address,)
    )
    rows = c.fetchall()
    conn.close()

    if not rows:
        await message.reply(
            f"📍 {address}\n\n"
            f"Zatím žádné poznámky.\n"
            f"Buďte první: /add {address} vaše_poznámka"
        )
        return

    response = f"📍 {address}\n\n"
    for note, updated in rows:
        try:
            days_ago = (datetime.now() - datetime.fromisoformat(updated)).days
            if days_ago == 0:
                time_text = "dnes"
            elif days_ago == 1:
                time_text = "včera"
            elif days_ago < 5:
                time_text = f"před {days_ago} dny"
            else:
                time_text = f"před {days_ago} dny"
        except Exception:
            time_text = "datum neznámé"

        response += f"• {note} ({time_text})\n"

    await message.reply(response)


@dp.message(Command("fix"))
async def fix_note(message: types.Message):
    text = message.text.replace("/fix", "").strip()
    parts = text.split(" ", 2)

    if len(parts) < 3:
        await message.reply(
            "❌ Špatný formát.\n\n"
            "Formát: /fix Ulice číslo staré nové\n"
            "Příklad: /fix Vinohradska 15 kod 5678"
        )
        return

    address = (parts[0] + " " + parts[1]).lower().strip()
    old_part = parts[2].split(" ")[0].strip()
    new_part = " ".join(parts[2].split(" ")[1:]).strip()
    now = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE notes SET note = ?, updated_at = ? "
        "WHERE address = ? AND note LIKE ?",
        (new_part, now, address, f"%{old_part}%")
    )
    updated = c.rowcount
    conn.commit()
    conn.close()

    if updated:
        await message.reply(f"✅ Aktualizováno: {old_part} → {new_part}")
    else:
        await message.reply(
            f"❌ Nenašel jsem poznámku s '{old_part}' pro {address}.\n"
            f"Zkontrolujte adresu: /get {address}"
        )


@dp.message()
async def any_message(message: types.Message):
    await message.reply(
        "Rozumím jen příkazům.\n"
        "Napište /help pro seznam."
    )


async def main():
    init_db()
    print("Bot startuje v polling režimu...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())