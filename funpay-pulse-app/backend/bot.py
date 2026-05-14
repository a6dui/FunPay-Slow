import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Get the directory where main.py/bot.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "funpaypulse.db")

# BOT TOKEN (User should replace this with their actual token from @BotFather)
API_TOKEN = '8997989380:AAFLk64Xrwe1ebr7LZMxaLuoDnT2Kg-P9-M' # Placeholder

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

from aiogram.filters import Command, CommandObject

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    args = command.args
    if args and len(args) == 6 and args.isdigit():
        # Automatic confirmation via deep link
        await process_code(message, args)
    else:
        await message.answer(
            "👋 **Добро пожаловать в FunPay Slow!**\n\n"
            "Чтобы войти в панель управления, отправьте мне 6-значный код, который вы видите в приложении.",
            parse_mode="Markdown"
        )

@dp.message()
async def handle_message(message: types.Message):
    code = message.text.strip()
    if len(code) == 6 and code.isdigit():
        await process_code(message, code)
    else:
        # Ignore other messages
        pass

async def process_code(message, code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if code exists in DB
    c.execute("SELECT code FROM auth_codes WHERE code = ?", (code,))
    row = c.fetchone()
    
    if row:
        # Mark as confirmed
        c.execute("UPDATE auth_codes SET confirmed = 1, user_first_name = ? WHERE code = ?", 
                  (message.from_user.first_name, code))
        conn.commit()
        conn.close()
        
        await message.answer(
            f"👋 С возвращением, {message.from_user.first_name}!\n\n"
            "✅ **Авторизация в FunPay Slow успешна!**\n"
            "Вернитесь в приложение — панель уже открыта.",
            parse_mode="Markdown"
        )
    else:
        conn.close()
        await message.answer(
            "❌ **Ошибка: Код не найден или уже использован.**\n"
            "Получите новый код в приложении.",
            parse_mode="Markdown"
        )

async def main():
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
