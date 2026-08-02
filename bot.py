import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = "prague_kurier_notes.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
