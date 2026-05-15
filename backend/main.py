import asyncio
import sqlite3
import os
import hashlib
import random
import string
import requests
import psycopg2
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from contextlib import asynccontextmanager
from psycopg2.extras import RealDictCursor

# --- SETTINGS & CONFIG ---
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "funpaypulse.db")
SNIPER_DB_FILE = os.path.join(BASE_DIR, "sniper.db")

# --- Bot Initialization ---
bot_obj = None
dp = Dispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot_obj
    if BOT_TOKEN:
        bot_obj = Bot(token=BOT_TOKEN)
        loop = asyncio.get_event_loop()
        loop.create_task(dp.start_polling(bot_obj))
        print(">>> Telegram Bot started in background")
    else:
        print(">>> WARNING: BOT_TOKEN not found. Bot disabled.")
    yield
    if bot_obj:
        await bot_obj.session.close()

app = FastAPI(title="FunPay Slow API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE HELPERS ---
def get_db_conn():
    if DATABASE_URL:
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
        conn = psycopg2.connect(db_url, sslmode='require')
        return conn
    else:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

def get_ph():
    return "%s" if DATABASE_URL else "?"

def generate_referral_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    is_postgres = DATABASE_URL is not None
    pk = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    tables = [
        f"CREATE TABLE IF NOT EXISTS users (id {pk}, name TEXT, username TEXT, email TEXT UNIQUE, password_hash TEXT, balance REAL DEFAULT 0, is_admin INTEGER DEFAULT 0, tg_id TEXT, created_at TEXT)",
        "CREATE TABLE IF NOT EXISTS auth_codes (code TEXT PRIMARY KEY, confirmed INTEGER DEFAULT 0, user_first_name TEXT, user_id TEXT, expires_at TEXT)",
        "CREATE TABLE IF NOT EXISTS subscriptions (user_id TEXT PRIMARY KEY, plan TEXT, expires_at TEXT, status TEXT DEFAULT 'inactive', trial_used INTEGER DEFAULT 0)",
        f"CREATE TABLE IF NOT EXISTS plugins (id {pk}, title TEXT, description TEXT, price TEXT, icon TEXT)",
        "CREATE TABLE IF NOT EXISTS referral_stats (user_id TEXT PRIMARY KEY, referral_code TEXT UNIQUE NOT NULL, referrer_id TEXT, balance REAL DEFAULT 0, invited_count INTEGER DEFAULT 0, level INTEGER DEFAULT 1)",
        f"CREATE TABLE IF NOT EXISTS referrals_list (id {pk}, referrer_id TEXT, referred_id TEXT, created_at TEXT)",
        "CREATE TABLE IF NOT EXISTS payments (invoice_id TEXT PRIMARY KEY, user_id TEXT, amount REAL, plan_id TEXT, status TEXT, created_at TEXT)"
    ]
    
    for sql in tables:
        c.execute(sql)
    
    c.execute("SELECT COUNT(*) FROM plugins")
    if c.fetchone()[0] == 0:
        ph = get_ph()
        defaults = [
            ('AutoRobux', 'Выдача Robux через Roblox Game Pass.', 'Официальный', '🤖'),
            ('AutoDiscordBoost', 'Автоматический Discord boost по заказам.', 'Официальный', '💎'),
            ('AutoStars', 'Автоматическая выдача Telegram Stars.', 'Официальный', '⭐'),
            ('Offline Activite', 'Выдача Steam Guard кодов по команде !guard.', 'Официальный', '🌙'),
            ('CopyLots', 'Копирование лотов между аккаунтами FunPay.', 'Официальный', '📋'),
            ('ChatSpam', 'Массовая отправка сообщений в чаты FunPay.', 'Официальный', '💬')
        ]
        for p in defaults:
            c.execute(f"INSERT INTO plugins (title, description, price, icon) VALUES ({ph}, {ph}, {ph}, {ph})", p)
            
    conn.commit()
    conn.close()
    print(f">>> DB Initialized ({'PostgreSQL' if is_postgres else 'SQLite'})")

init_db()

# --- MODELS ---
class SupportMessage(BaseModel):
    user_id: str
    username: str
    message: str
    type: str = "support"

class TrialRequest(BaseModel):
    user_id: str

class BalanceUpdate(BaseModel):
    user_id: str
    amount: float
    admin_id: str

# --- CORE FUNCTIONS ---
def send_admin_tg(message: str):
    if not BOT_TOKEN or not ADMIN_CHAT_ID: return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def ensure_referral_stats(user_id: str):
    conn = get_db_conn()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f"SELECT user_id FROM referral_stats WHERE user_id = {ph}", (str(user_id),))
    if not c.fetchone():
        code = generate_referral_code()
        c.execute(f"INSERT INTO referral_stats (user_id, referral_code) VALUES ({ph}, {ph})", (str(user_id), code))
        conn.commit()
    conn.close()

# --- ENDPOINTS ---
@app.get("/")
def root(): return {"status": "ok", "version": "2.4.1"}

@app.get("/api/plugins")
def get_plugins():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, title, description, price, icon FROM plugins")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "description": r[2], "price": r[3], "icon": r[4]} for r in rows]

@app.get("/api/auth/init/{code}")
def init_auth(code: str):
    conn = get_db_conn()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f"DELETE FROM auth_codes WHERE code = {ph}", (code,))
    c.execute(f"INSERT INTO auth_codes (code, confirmed) VALUES ({ph}, 0)", (code,))
    conn.commit()
    conn.close()
    return {"status": "waiting"}

@app.get("/api/auth/check/{code}")
def check_auth(code: str):
    conn = get_db_conn()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f"SELECT confirmed, user_first_name, user_id FROM auth_codes WHERE code = {ph}", (code,))
    row = c.fetchone()
    conn.close()
    if row and row[0] == 1:
        ensure_referral_stats(row[2])
        return {"success": True, "name": row[1], "user_id": row[2]}
    return {"success": False}

@app.get("/api/user/subscription/{user_id}")
def get_sub(user_id: str):
    conn = get_db_conn()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f"SELECT plan, expires_at, status FROM subscriptions WHERE user_id = {ph}", (str(user_id),))
    row = c.fetchone()
    conn.close()
    if row: return {"plan": row[0], "expires_at": row[1], "status": row[2]}
    return {"plan": "Бесплатно", "expires_at": "-", "status": "inactive"}

@app.get("/api/user/referral/{user_id}")
def get_referral(user_id: str):
    ensure_referral_stats(user_id)
    conn = get_db_conn()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f"SELECT referral_code, balance, invited_count, level FROM referral_stats WHERE user_id = {ph}", (str(user_id),))
    row = c.fetchone()
    c.execute(f"SELECT user_id, created_at FROM referrals_list WHERE referrer_id = {ph} ORDER BY id DESC", (str(user_id),))
    friends = [{"username": f"User {r[0][-4:]}", "date": r[1]} for r in c.fetchall()]
    conn.close()
    if row: return {"referral_code": row[0], "balance": row[1], "invited_count": row[2], "level": row[3], "referrals": friends}
    return None

# --- ADMIN ENDPOINTS ---
def is_admin(user_id: str):
    admin_ids = ["6360699049", "5304677735", "755843448"]
    return str(user_id) in admin_ids

@app.get("/api/admin/stats")
def get_admin_stats(admin_id: str):
    if not is_admin(admin_id): raise HTTPException(status_code=403)
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    u_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
    a_subs = c.fetchone()[0]
    c.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
    sales = c.fetchone()[0] or 0
    conn.close()
    return {
        "total_users": u_count,
        "online_users": random.randint(1, u_count + 5) if u_count > 0 else 0,
        "active_subs": a_subs,
        "total_sales": f"{sales} руб.",
        "total_plugins": 6
    }

@app.get("/api/admin/payments")
def get_admin_payments(admin_id: str):
    if not is_admin(admin_id): raise HTTPException(status_code=403)
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT invoice_id, user_id, amount, plan_id, status, created_at FROM payments ORDER BY created_at DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "user_id": r[1], "amount": r[2], "plan": r[3], "status": r[4], "date": r[5]} for r in rows]

@app.post("/api/admin/balance/update")
def update_user_balance(req: BalanceUpdate):
    if not is_admin(req.admin_id): raise HTTPException(status_code=403)
    conn = get_db_conn()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f"SELECT balance FROM users WHERE tg_id = {ph}", (str(req.user_id),))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "User not found"}
    new_balance = max(0, row[0] + req.amount)
    c.execute(f"UPDATE users SET balance = {ph} WHERE tg_id = {ph}", (new_balance, str(req.user_id)))
    conn.commit()
    conn.close()
    send_admin_tg(f"💰 Админ {req.admin_id} изменил баланс пользователя {req.user_id} на {req.amount}. Новый баланс: {new_balance}")
    return {"success": True, "new_balance": new_balance}

# --- BOT HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    args = command.args
    if args and len(args) == 6 and args.isdigit():
        await process_auth(message, args)
    else:
        await message.answer("👋 Добро пожаловать! Отправьте код из приложения для входа.")

@dp.message()
async def handle_msg(message: types.Message):
    if message.text and len(message.text) == 6 and message.text.isdigit():
        await process_auth(message, message.text)

async def process_auth(message, code):
    conn = get_db_conn()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f"SELECT code FROM auth_codes WHERE code = {ph}", (code,))
    if c.fetchone():
        c.execute(f"UPDATE auth_codes SET confirmed = 1, user_first_name = {ph}, user_id = {ph} WHERE code = {ph}", 
                  (message.from_user.first_name, str(message.from_user.id), code))
        c.execute(f"SELECT id FROM users WHERE tg_id = {ph}", (str(message.from_user.id),))
        if not c.fetchone():
            c.execute(f"INSERT INTO users (tg_id, name, created_at) VALUES ({ph}, {ph}, {ph})", 
                      (str(message.from_user.id), message.from_user.first_name, datetime.now().isoformat()))
        conn.commit()
        await message.answer("✅ Авторизация успешна! Вернитесь на сайт.")
    else:
        await message.answer("❌ Код недействителен.")
    conn.close()
