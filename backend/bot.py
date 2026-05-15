import asyncio
import sqlite3
import os
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Sync with main.py DB
DB_FILE = os.path.join(BASE_DIR, "funpay_slow.db")

# BOT TOKEN
API_TOKEN = '8997989380:AAFLk64Xrwe1ebr7LZMxaLuoDnT2Kg-P9-M'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    print(f">>> Received /start from {message.from_user.id}")
    args = command.args
    if args and len(args) == 6 and args.isdigit():
        await process_code(message, args)
    else:
        await message.answer(
            "👋 **Добро пожаловать в FunPay Slow!**\n\n"
            "Чтобы войти в панель управления, отправьте мне 6-значный код, который вы видите на сайте.",
            parse_mode="Markdown"
        )

@dp.message()
async def handle_message(message: types.Message):
    if not message.text: return
    code = message.text.strip()
    if len(code) == 6 and code.isdigit():
        await process_code(message, code)

async def process_code(message, code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Check if code exists in auth_tokens
    c.execute("SELECT token FROM auth_tokens WHERE code = ?", (code,))
    row = c.fetchone()
    
    if row:
        token = row[0]
        user_id = str(message.from_user.id)
        first_name = message.from_user.first_name or "User"
        username = message.from_user.username or "none"
        
        # 2. Update auth_token with user_id to unlock the web session
        c.execute("UPDATE auth_tokens SET user_id = ? WHERE code = ?", (user_id, code))
        
        # 3. Create or update user in users table
        now = int(time.time())
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, plan, created_at) VALUES (?, ?, ?, 'none', ?)", 
                  (user_id, first_name, username, now))
        
        conn.commit()
        conn.close()
        
        await message.answer(
            f"✅ **Авторизация успешна!**\n\n"
            f"С возвращением, **{first_name}**!\n"
            f"Ваш ID: `{user_id}`\n\n"
            "Вернитесь на сайт — вход выполнен автоматически. 🐌",
            parse_mode="Markdown"
        )
    else:
        conn.close()
        await message.answer(
            "❌ **Ошибка: Код не найден.**\n"
            "Убедитесь, что вы ввели правильный код из приложения FunPay Slow.",
            parse_mode="Markdown"
        )

async def main():
    print("🚀 FunPay Slow Bot is starting...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
