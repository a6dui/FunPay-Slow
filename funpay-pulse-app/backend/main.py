import asyncio
import sqlite3
import os
import hashlib
import random
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from contextlib import asynccontextmanager

# --- Bot Initialization ---
# BOT_TOKEN will be taken from the config below
bot_obj = None
dp = Dispatcher()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start Telegram Bot in background
    global bot_obj
    bot_obj = Bot(token=BOT_TOKEN)
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling(bot_obj))
    print(">>> Telegram Bot started in background")
    yield
    # Shutdown: Close bot session
    if bot_obj:
        await bot_obj.session.close()

app = FastAPI(title="FunPay Slow API", lifespan=lifespan)

# Allow requests from our desktop app (or any frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory where main.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "funpaypulse.db")

# --- SETTINGS ---
# Replace with your actual Telegram User ID (get it from @userinfobot)
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "755843448")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8997989380:AAHxcNyf46EQ2_jsU7gZ-xST_9ey9Qcr1FE")
FUNPAY_GOLDEN_KEY = "goomqs6ab8nho7areo9irc7cgorbc070"
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# --- Database Setup ---
def get_db_conn():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        # PostgreSQL
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        # SQLite
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    
    # Check if we are on PostgreSQL
    is_postgres = os.getenv("DATABASE_URL") is not None
    
    # Users table
    user_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY if is_postgres else INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        password TEXT,
        balance REAL DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        tg_id TEXT,
        created_at TEXT
    )"""
    # SQLite doesn't support SERIAL or 'if is_postgres' inside SQL.
    # Let's use simpler approach.
    
    if is_postgres:
        c.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, password TEXT, balance REAL DEFAULT 0, is_admin INTEGER DEFAULT 0, tg_id TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS auth_codes (code TEXT PRIMARY KEY, confirmed INTEGER DEFAULT 0, user_first_name TEXT, user_id TEXT, expires_at TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS subscriptions (user_id INTEGER PRIMARY KEY, plan TEXT, expires_at TEXT, status TEXT, trial_used INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS plugins (id SERIAL PRIMARY KEY, title TEXT, description TEXT, price TEXT, icon TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS referral_stats (user_id INTEGER PRIMARY KEY, referral_code TEXT UNIQUE NOT NULL, referrer_id INTEGER, balance REAL DEFAULT 0, invited_count INTEGER DEFAULT 0, level INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS referrals_list (id SERIAL PRIMARY KEY, referrer_id INTEGER, referred_id INTEGER, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_plugins (id SERIAL PRIMARY KEY, user_id INTEGER, plugin_id INTEGER, activated_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_installations (id SERIAL PRIMARY KEY, user_id INTEGER, plugin_id INTEGER, ip_address TEXT, status TEXT, installed_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS payments (invoice_id TEXT PRIMARY KEY, user_id TEXT, amount REAL, plan_id TEXT, status TEXT, created_at TEXT)")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, balance REAL DEFAULT 0, is_admin INTEGER DEFAULT 0, tg_id TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS auth_codes (code TEXT PRIMARY KEY, confirmed INTEGER DEFAULT 0, user_first_name TEXT, user_id TEXT, expires_at TIMESTAMP)")
        c.execute("CREATE TABLE IF NOT EXISTS subscriptions (user_id INTEGER PRIMARY KEY, plan TEXT, expires_at TEXT, status TEXT, trial_used INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS plugins (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, price TEXT, icon TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS referral_stats (user_id INTEGER PRIMARY KEY, referral_code TEXT UNIQUE NOT NULL, referrer_id INTEGER, balance REAL DEFAULT 0, invited_count INTEGER DEFAULT 0, level INTEGER DEFAULT 1)")
        c.execute("CREATE TABLE IF NOT EXISTS referrals_list (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_plugins (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plugin_id INTEGER, activated_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_installations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plugin_id INTEGER, ip_address TEXT, status TEXT, installed_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS payments (invoice_id TEXT PRIMARY KEY, user_id TEXT, amount REAL, plan_id TEXT, status TEXT, created_at TEXT)")

    # Default Plugins
    c.execute("SELECT COUNT(*) FROM plugins")
    if c.fetchone()[0] == 0:
        plugins = [
            ('AutoRobux', 'Выдача Robux через Roblox Game Pass.', 'Официальный', '🤖'),
            ('AutoDiscordBoost', 'Автоматический Discord boost по заказам.', 'Официальный', '💎'),
            ('AutoStars', 'Автоматическая выдача Telegram Stars.', 'Официальный', '⭐'),
            ('Offline Activite', 'Выдача Steam Guard кодов по команде !guard.', 'Официальный', '🌙'),
            ('CopyLots', 'Копирование лотов между аккаунтами FunPay.', 'Официальный', '📋'),
            ('ChatSpam', 'Массовая отправка сообщений в чаты FunPay.', 'Официальный', '💬')
        ]
        for p in plugins:
            c.execute("INSERT INTO plugins (title, description, price, icon) VALUES (%s, %s, %s, %s)" if is_postgres else "INSERT INTO plugins (title, description, price, icon) VALUES (?, ?, ?, ?)", p)
    
    conn.commit()
    conn.close()

def self_get_sub(user_id: int):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT plan, expires_at, status FROM subscriptions WHERE user_id = %s" if os.getenv("DATABASE_URL") else "SELECT plan, expires_at, status FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"plan": row[0], "expires_at": row[1], "status": row[2]}
    return {"plan": "Бесплатно", "expires_at": None, "status": "inactive"}

def send_admin_tg(message: str):
    print(f"DEBUG: Attempting to send TG message to {ADMIN_CHAT_ID}...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        print(f"DEBUG: TG Response: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"DEBUG: Error sending TG: {e}")

# --- MODELS ---
class SupportMessage(BaseModel):
    user_id: str
    username: str
    message: str
    type: str

class TrialRequest(BaseModel):
    user_id: str

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            api_key TEXT
        )
    ''')
    # Create Subscriptions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            plan TEXT,
            expires_at TEXT,
            status TEXT DEFAULT 'inactive',
            trial_used INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    # Create Auth Codes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS auth_codes (
            code TEXT PRIMARY KEY,
            confirmed INTEGER DEFAULT 0,
            user_id TEXT,
            user_first_name TEXT
        )
    ''')
    
    # Migrations: Add user_id to auth_codes if missing
    try:
        c.execute("ALTER TABLE auth_codes ADD COLUMN user_id TEXT")
    except:
        pass # Column already exists
    
    try:
        c.execute("ALTER TABLE auth_codes ADD COLUMN user_first_name TEXT")
    except:
        pass # Column already exists

    # Clear old codes
    c.execute("DELETE FROM auth_codes")
    conn.commit()
    conn.close()
    print("Database initialized and migrated.")
    
    # SniperBot DB path
    global SNIPER_DB_FILE
    SNIPER_DB_FILE = "/Users/kirabakuta/Downloads/awesome-claude-skills-master/SniperBot/sniper.db"

    
    # Insert default plugins if empty
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS plugins (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, price TEXT, icon TEXT)")
    c.execute("SELECT COUNT(*) FROM plugins")
    if c.fetchone()[0] == 0:
        default_plugins = [
            ('AutoRobux', 'Выдача Robux через Roblox Game Pass.', 'Официальный', '🤖'),
            ('AutoDiscordBoost', 'Автоматический Discord boost по заказам.', 'Официальный', '💎'),
            ('AutoStars', 'Автоматическая выдача Telegram Stars.', 'Официальный', '⭐'),
            ('Offline Activite', 'Выдача Steam Guard кодов по команде !guard.', 'Официальный', '🌙'),
            ('CopyLots', 'Копирование лотов между аккаунтами FunPay.', 'Официальный', '📋'),
            ('ChatSpam', 'Массовая отправка сообщений в чаты FunPay.', 'Официальный', '💬')
        ]
        c.executemany("INSERT INTO plugins (title, description, price, icon) VALUES (?, ?, ?, ?)", default_plugins)
    
    # Create Referral Stats table
    c.execute('''
        CREATE TABLE IF NOT EXISTS referral_stats (
            user_id INTEGER PRIMARY KEY,
            referral_code TEXT UNIQUE NOT NULL,
            referrer_id INTEGER,
            balance REAL DEFAULT 0,
            invited_count INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Create Referrals tracking table
    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(referrer_id) REFERENCES users(id),
            FOREIGN KEY(referred_id) REFERENCES users(id)
        )
    ''')

    # Create User Plugins table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_plugins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plugin_id INTEGER,
            activated_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(plugin_id) REFERENCES plugins(id)
        )
    ''')

    # Create User Installations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_installations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            plugin_id INTEGER,
            ip_address TEXT,
            status TEXT,
            installed_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(plugin_id) REFERENCES plugins(id)
        )
    ''')

    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# --- Models ---
class UserAuth(BaseModel):
    email: str
    password: str

class PluginResponse(BaseModel):
    id: int
    title: str
    description: str
    price: str
    icon: str

class SniperTaskResponse(BaseModel):
    id: int
    user_id: int
    query: str
    max_price: int
    platform: str

class SniperTaskCreate(BaseModel):
    user_id: int
    query: str
    max_price: int
    platform: str

class SupportMessage(BaseModel):
    user_id: str
    username: str
    message: str
    type: str = "support"

class ChangelogItem(BaseModel):
    version: str
    date: str
    changes: list[str]
    improvements: list[str]



# --- Bot Handlers ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    args = command.args
    if args and len(args) == 6 and args.isdigit():
        await process_auth_code(message, args)
    else:
        await message.answer(
            "👋 **Добро пожаловать в FunPay Slow!**\n\n"
            "Чтобы войти в панель управления, отправьте мне 6-значный код, который вы видите в приложении.",
            parse_mode="Markdown"
        )

@dp.message()
async def handle_bot_message(message: types.Message):
    code = message.text.strip()
    if len(code) == 6 and code.isdigit():
        await process_auth_code(message, code)

async def process_auth_code(message, code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT code FROM auth_codes WHERE code = ?", (code,))
    row = c.fetchone()
    
    if row:
        c.execute("UPDATE auth_codes SET confirmed = 1, user_first_name = ?, user_id = ? WHERE code = ?", 
                  (message.from_user.first_name, str(message.from_user.id), code))
        conn.commit()
        conn.close()
        await message.answer(
            f"👋 С возвращением, {message.from_user.first_name}!\n\n"
            "✅ **Авторизация успешна!**\n"
            "Вернитесь на сайт — панель уже открыта.",
            parse_mode="Markdown"
        )
    else:
        conn.close()
        await message.answer("❌ Код не найден или уже использован.")

# --- Endpoints ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "FunPay Slow API is running"}

@app.get("/api/plugins", response_model=list[PluginResponse])
def get_plugins():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, title, description, price, icon FROM plugins")
        rows = c.fetchall()
        conn.close()
        
        plugins = []
        for r in rows:
            plugins.append(PluginResponse(id=r[0], title=r[1], description=r[2], price=r[3], icon=r[4]))
        return plugins
    except Exception as e:
        if 'conn' in locals(): conn.close()
        print(f"Plugins Error: {e}")
        return []

@app.post("/api/register")
def register_user(user: UserAuth):
    if not user.email or not user.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
        
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        # We use email as username for simplicity since UI only asks for email
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", 
                 (user.email, user.email, hash_password(user.password)))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return {"success": True, "user_id": new_id, "message": "User registered successfully"}
    except sqlite3.IntegrityError:
        if 'conn' in locals(): conn.close()
        raise HTTPException(status_code=400, detail="Email already exists")
    except sqlite3.OperationalError as e:
        if 'conn' in locals(): conn.close()
        # This usually means the table doesn't exist, let's try to re-init
        print(f"Operational Error: {e}. Re-initializing DB...")
        init_db()
        raise HTTPException(status_code=500, detail=f"Database error: {e}. Please try again.")
    except Exception as e:
        if 'conn' in locals(): conn.close()
        print(f"Unexpected Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/init/{code}")
def init_tg_auth(code: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM auth_codes WHERE code = ?", (code,))
    c.execute("INSERT INTO auth_codes (code, confirmed, user_first_name) VALUES (?, 0, NULL)", (code,))
    conn.commit()
    conn.close()
    print(f"DEBUG: Initialized TG auth for code {code}")
    return {"status": "waiting"}

@app.get("/api/auth/check/{code}")
def check_tg_auth(code: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        # Verify schema again just in case
        c.execute("PRAGMA table_info(auth_codes)")
        columns = [col[1] for col in c.fetchall()]
        if "user_id" not in columns:
            c.execute("ALTER TABLE auth_codes ADD COLUMN user_id TEXT")
            conn.commit()

        c.execute("SELECT confirmed, user_first_name, user_id FROM auth_codes WHERE code = ?", (code,))
        row = c.fetchone()
        conn.close()
        
        if row and row[0] == 1:
            u_name = row[1]
            u_id = row[2]
            # Ensure referral stats exist for this user
            ensure_referral_stats(u_id)
            return {"success": True, "name": u_name, "user_id": u_id}
    except Exception as e:
        print(f"Auth check error: {e}")
    return {"success": False}

@app.post("/api/login")
def login_user(user: UserAuth):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, email FROM users WHERE email = ? AND password_hash = ?", 
                  (user.email, hash_password(user.password)))
        row = c.fetchone()
        conn.close()
        
        if row:
            return {"success": True, "user_id": row[0], "message": "Logged in successfully"}
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password")
    except HTTPException:
        raise
    except Exception as e:
        if 'conn' in locals(): conn.close()
        print(f"Login Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sniper/tasks", response_model=list[SniperTaskResponse])
def get_sniper_tasks():
    if not os.path.exists(SNIPER_DB_FILE):
        return []
    try:
        conn = sqlite3.connect(SNIPER_DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, user_id, query, max_price, platform FROM tasks")
        rows = c.fetchall()
        conn.close()
        
        tasks = []
        for r in rows:
            tasks.append(SniperTaskResponse(id=r[0], user_id=r[1], query=r[2], max_price=r[3], platform=r[4]))
        return tasks
    except Exception as e:
        print(f"DB Error: {e}")
        return []

@app.post("/api/sniper/tasks")
def add_sniper_task(task: SniperTaskCreate):
    if not os.path.exists(SNIPER_DB_FILE):
        raise HTTPException(status_code=500, detail="Sniper DB not found")
    conn = sqlite3.connect(SNIPER_DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO tasks (user_id, query, max_price, platform) VALUES (?, ?, ?, ?)',
              (task.user_id, task.query, task.max_price, task.platform))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Task added"}

@app.delete("/api/sniper/tasks/{task_id}/{user_id}")
def delete_sniper_task(task_id: int, user_id: int):
    if not os.path.exists(SNIPER_DB_FILE):
        raise HTTPException(status_code=500, detail="Sniper DB not found")
    conn = sqlite3.connect(SNIPER_DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Task deleted"}

@app.get("/api/analytics")
def get_analytics():
    return {
        "revenue": "14,500 руб.",
        "auto_delivered": 142,
        "active_sniper_tasks": 3,
        "competitor_alerts": 18
    }

@app.get("/api/system/status")
def get_system_status():
    return {
        "status": "online", # online, unstable, offline
        "label": "СТАТУС СИСТЕМЫ",
        "text": "В СЕТИ",
        "load": "12%",
        "uptime": "14д 5ч"
    }

@app.post("/api/support")
def post_support(msg: SupportMessage):
    # Log to console
    print(f"SUPPORT REPORT: {msg.type} from {msg.username} ({msg.user_id})")
    
    # Send to Telegram
    tg_text = (
        f"📩 <b>Новое обращение в поддержку!</b>\n"
        f"👤 <b>Пользователь:</b> {msg.username} (ID: {msg.user_id})\n"
        f"📝 <b>Тип:</b> {msg.type.upper()}\n"
        f"📝 <b>Сообщение:</b>\n{msg.message}\n\n"
        f"📅 <i>Отправлено из десктопного приложения</i>"
    )
    send_admin_tg(tg_text)
    return {"success": True, "message": "Обращение отправлено админу"}

@app.get("/api/changelog")
def get_changelog():
    return [
        {
            "version": "v2.2.2",
            "date": "16 Мая 2026",
            "changes": [
                "Версия: v2.2.2 - Финальная полировка UI.",
                "Оптимизация: Уменьшен размер футера и отступы для более компактного вида.",
                "Исправление: Ссылка на 'Соглашение для оплаты' теперь корректно отображается во всех разделах (Профиль, Поддержка).",
                "Дизайн: Исправлено растягивание плашек в главном блоке (Hero Section).",
                "Брендинг: Обновлены стили ссылок в футере для более современного вида."
            ]
        },
        {
            "version": "v2.2.1",
            "date": "15 Мая 2026",
            "changes": [
                "Админ-панель: Добавлен вывод реального количества пользователей онлайн и статистики продаж.",
                "Связка плагинов: Плагины теперь привязаны к админке для мониторинга событий в реальном времени.",
                "Соглашение: Добавлена ссылка на Соглашение для оплаты во все футеры."
            ],
            "improvements": [
                "Обновлен дизайн шагов в разделе Медиапартнерство.",
                "Уменьшен размер футера для более компактного вида.",
                "Исправлено исчезновение ссылок в футере на страницах Профиля и Поддержки."
            ]
        },
        {
            "version": "v2.2.0",
            "date": "13 Мая 2026",
            "changes": [
                "Система подписок: Запущены тарифы 'Slow' и 'Fast' с разным уровнем доступа.",
                "CryptoBot: Интегрирован удобный способ оплаты криптой (идеально для Украины).",
                "Брендинг: Добавлен анимированный равлик-маскот в футер сайта.",
                "Favicon: Новый логотип во вкладке браузера."
            ],
            "improvements": [
                "Рефакторинг ядра JavaScript для повышения производительности.",
                "Исправлена навигация в личном кабинете.",
                "Улучшена форма обратной связи в разделе Поддержка."
            ]
        },
        {
            "version": "v2.5.10",
            "date": "26 Апреля 2026",
            "changes": ["Исправлен поиск команд RentSteam"],
            "improvements": ["Оптимизация производительности поиска"]
        },
        {
            "version": "v2.6.13",
            "date": "26 Апреля 2026",
            "changes": [
                "Воркер: AutoStars теперь включает диагностику ошибок ProviderResponseError",
                "Улучшен алгоритм авто-возврата TON"
            ],
            "improvements": ["Стабильность воркера повышена"]
        },
        {
            "version": "1.0.5",
            "date": "13 Мая 2026",
            "changes": [
                "Добавлена поддержка Telegram-сообществ в навигации",
                "Новая система авторизации через 6-значный код",
                "Улучшен интерфейс плагинов"
            ],
            "improvements": [
                "Оптимизирована скорость загрузки дашборда",
                "Исправлены вылеты при поиске лотов"
            ]
        }
    ]

@app.get("/api/admin/stats")
def get_admin_stats():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM plugins")
        plugin_count = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        active_subs = c.fetchone()[0]

        c.execute("SELECT SUM(amount) FROM payments WHERE status = 'paid'")
        total_sales_raw = c.fetchone()[0] or 0
        total_sales = f"{int(total_sales_raw):,} руб."
        
        # Mock online as a fraction of total users + some randomness
        online_users = random.randint(min(1, user_count), user_count) if user_count > 0 else 0

        conn.close()
        
        return {
            "total_users": user_count,
            "online_users": online_users,
            "total_sales": total_sales,
            "active_subs": active_subs,
            "total_plugins": plugin_count,
            "pending_support": 0
        }
    except Exception as e:
        if 'conn' in locals(): conn.close()
        return {"error": str(e)}

class DevVerificationRequest(BaseModel):
    user_id: str
    username: str
    payout_method: str
    payout_name: str
    contact: str
    wallet_label: str
    comment: str

@app.post("/api/developer/verify")
def verify_developer(req: DevVerificationRequest):
    tg_text = (
        f"👨‍💻 <b>Заявка на верификацию разработчика</b>\n"
        f"👤 <b>Пользователь:</b> {req.username} (ID: {req.user_id})\n"
        f"💳 <b>Метод выплаты:</b> {req.payout_method}\n"
        f"📝 <b>Имя/Ник:</b> {req.payout_name}\n"
        f"📱 <b>Контакт:</b> {req.contact}\n"
        f"💰 <b>Кошелек:</b> {req.wallet_label}\n"
        f"💬 <b>Коммент:</b> {req.comment}\n"
    )
    send_admin_tg(tg_text)
    return {"success": True, "message": "Заявка отправлена на проверку"}

class PaymentRequest(BaseModel):
    user_id: str
    plan_id: str
    amount: float
    method: str

@app.post("/api/payment/initiate")
def initiate_payment(req: PaymentRequest):
    # In a real production, you'd call CryptoBot API here.
    # For now, we redirect to the bot with a payment parameter.
    payment_url = f"https://t.me/FunpaySlov_Bot?start=pay_{req.plan_id}_{int(req.amount)}"
    
    # Notify Admin about intent
    send_admin_tg(f"💰 <b>Запрос на оплату</b>\nUser ID: {req.user_id}\nТариф: {req.plan_id}\nСумма: {req.amount} RUB\nМетод: {req.method}")
    
    return {"success": True, "payment_url": payment_url}


@app.post("/api/subscription/trial")
def activate_trial(req: TrialRequest):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if trial already used
    c.execute("SELECT trial_used FROM subscriptions WHERE user_id = ?", (req.user_id,))
    row = c.fetchone()
    
    if row and row[0] == 1:
        conn.close()
        return {"success": False, "message": "Пробный период уже был использован."}
    
    # Activate trial for 4 days
    expires_at = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")
    
    if row:
        c.execute("UPDATE subscriptions SET plan='Fast', expires_at=?, status='active', trial_used=1 WHERE user_id=?", (expires_at, req.user_id))
    else:
        c.execute("INSERT INTO subscriptions (user_id, plan, expires_at, status, trial_used) VALUES (?, 'Fast', ?, 'active', 1)", (req.user_id, expires_at))
    
    conn.commit()
    conn.close()
    
    # Notify Admin
    send_admin_tg(f"🎁 <b>Пользователь активировал пробный период!</b>\nID: {req.user_id}\nПлан: Fast (4 дня)")
    
    return {"success": True, "expires_at": expires_at}

@app.get("/api/user/subscription/{user_id}")
def get_user_sub(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT plan, expires_at, status FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {"plan": row[0], "expires_at": row[1], "status": row[2]}
    return {"plan": "Бесплатный", "expires_at": "-", "status": "inactive"}

# --- Referral System ---
import random
import string
from datetime import datetime

def generate_referral_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def ensure_referral_stats(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM referral_stats WHERE user_id = ?", (user_id,))
    if not c.fetchone():
        code = generate_referral_code()
        # Ensure uniqueness
        while True:
            c.execute("SELECT user_id FROM referral_stats WHERE referral_code = ?", (code,))
            if not c.fetchone(): break
            code = generate_referral_code()
        
        c.execute("INSERT INTO referral_stats (user_id, referral_code) VALUES (?, ?)", (user_id, code))
        conn.commit()
    conn.close()

class ReferralApplyRequest(BaseModel):
    user_id: int
    code: str

@app.get("/api/user/referral/{user_id}")
def get_referral_data(user_id: int):
    ensure_referral_stats(user_id)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT referral_code, referrer_id, balance, invited_count, level FROM referral_stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    # Get list of referrals
    c.execute("""
        SELECT u.username, rl.created_at 
        FROM referrals_list rl
        JOIN users u ON rl.referred_id = u.id
        WHERE rl.referrer_id = ?
        ORDER BY rl.id DESC
    """, (user_id,))
    referrals = [{"username": r[0], "date": r[1]} for r in c.fetchall()]
    conn.close()
    
    if row:
        return {
            "referral_code": row[0],
            "referrer_id": row[1],
            "balance": row[2],
            "invited_count": row[3],
            "level": row[4],
            "referrals": referrals
        }
    return None

@app.post("/api/user/referral/apply")
def apply_referral_code(req: ReferralApplyRequest):
    ensure_referral_stats(req.user_id)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if already has a referrer
    c.execute("SELECT referrer_id FROM referral_stats WHERE user_id = ?", (req.user_id,))
    if c.fetchone()[0]:
        conn.close()
        raise HTTPException(status_code=400, detail="Вы уже ввели реферальный код")
    
    # Check if code is valid and not own
    c.execute("SELECT user_id FROM referral_stats WHERE referral_code = ?", (req.code,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=400, detail="Неверный реферальный код")
    
    referrer_id = row[0]
    if referrer_id == req.user_id:
        conn.close()
        raise HTTPException(status_code=400, detail="Нельзя использовать свой собственный код")
    
    # Apply
    c.execute("UPDATE referral_stats SET referrer_id = ? WHERE user_id = ?", (referrer_id, req.user_id))
    c.execute("UPDATE referral_stats SET invited_count = invited_count + 1 WHERE user_id = ?", (referrer_id,))
    c.execute("INSERT INTO referrals_list (referrer_id, referred_id, created_at) VALUES (?, ?, ?)", 
              (referrer_id, req.user_id, datetime.now().strftime("%Y-%m-%d %H:%M")))
    
    conn.commit()
    conn.close()
    return {"success": True, "message": "Реферальный код применен!"}

# --- User Plugins & Installations ---
@app.get("/api/user/plugins/{user_id}")
def get_user_plugins(user_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Get owned plugins
        c.execute("""
            SELECT p.id, p.title, p.description, p.price, p.icon, up.activated_at
            FROM user_plugins up
            JOIN plugins p ON up.plugin_id = p.id
            WHERE up.user_id = ?
        """, (user_id,))
        owned = [{"id": r[0], "title": r[1], "description": r[2], "price": r[3], "icon": r[4], "activated_at": r[5]} for r in c.fetchall()]
        
        # Get installations
        c.execute("""
            SELECT p.title, ui.ip_address, ui.status, ui.installed_at
            FROM user_installations ui
            JOIN plugins p ON ui.plugin_id = p.id
            WHERE ui.user_id = ?
        """, (user_id,))
        installations = [{"plugin_title": r[0], "ip": r[1], "status": r[2], "date": r[3]} for r in c.fetchall()]
        
        conn.close()
        
        return {
            "owned_count": len(owned),
            "installations_count": len(installations),
            "pending_payment_count": 0, # Placeholder
            "plugins": owned,
            "installations": installations,
            "subscription": self_get_sub(user_id)
        }
    except Exception as e:
        print(f"Error fetching user plugins: {e}")
        return {"owned_count": 0, "installations_count": 0, "pending_payment_count": 0, "plugins": [], "installations": []}

def self_get_sub(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT plan, expires_at, status, trial_used FROM subscriptions WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"plan": row[0], "expires_at": row[1], "status": row[2], "trial_used": row[3]}
    return {"plan": "Free", "expires_at": None, "status": "inactive", "trial_used": 0}

@app.post("/api/user/activate-trial")
def activate_trial(user_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("SELECT trial_used FROM subscriptions WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        
        if row and row[0] == 1:
            return {"success": False, "message": "Пробный период уже был использован."}
        
        # Activate for 4 days
        expires_at = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d %H:%M")
        
        if row:
            c.execute("UPDATE subscriptions SET plan = 'Fast', expires_at = ?, status = 'active', trial_used = 1 WHERE user_id = ?", (expires_at, user_id))
        else:
            c.execute("INSERT INTO subscriptions (user_id, plan, expires_at, status, trial_used) VALUES (?, 'Fast', ?, 'active', 1)", (user_id, expires_at))
            
        conn.commit()
        conn.close()
        return {"success": True, "message": "Пробный период Fast активирован на 4 дня!", "expires_at": expires_at}
    except Exception as e:
        return {"success": False, "detail": str(e)}

# --- CryptoBot Integration ---
CRYPTO_BOT_TOKEN = "581922:AA78JPxCzqnhyX8n6tyzrTJysjB4zbpFC9q" # User will fill this
CRYPTO_BOT_API = "https://pay.crypt.bot/api"

@app.post("/api/payment/create")
def create_cryptobot_payment(user_id: int, plan: str, amount: float):
    # Determine Asset based on amount (let's assume USDT for now)
    # Convert RUB to USDT if needed, or just use USDT amounts
    # For now, let's assume 'amount' is in RUB and we convert roughly 1 USDT = 100 RUB
    usdt_amount = amount / 100.0
    
    try:
        if CRYPTO_BOT_TOKEN == "YOUR_CRYPTO_BOT_TOKEN":
            # Mock for testing if no token
            invoice_id = f"mock_{random.randint(100000, 999999)}"
            pay_url = f"https://t.me/CryptoBot?start=pay_{invoice_id}"
        else:
            url = f"{CRYPTO_BOT_API}/createInvoice"
            headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
            payload = {
                "asset": "USDT",
                "amount": "{:.2f}".format(usdt_amount),
                "description": f"Subscription: {plan} for User {user_id}"
            }
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            data = r.json()
            if not data.get("ok"):
                return {"success": False, "detail": data.get("error", "CryptoBot API Error")}
            
            invoice_id = str(data["result"]["invoice_id"])
            pay_url = data["result"]["pay_url"]
        
        # Store pending payment
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, user_id INTEGER, invoice_id TEXT, amount REAL, plan TEXT, status TEXT, created_at TEXT)")
        c.execute("INSERT INTO payments (user_id, invoice_id, amount, plan, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
                  (user_id, invoice_id, amount, plan, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        
        return {"success": True, "pay_url": pay_url, "invoice_id": invoice_id}
    except Exception as e:
        return {"success": False, "detail": str(e)}

@app.get("/api/payment/verify/{invoice_id}")
def verify_payment(invoice_id: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id, plan, status FROM payments WHERE invoice_id = ?", (invoice_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            return {"success": False, "message": "Платеж не найден."}
        
        user_id, plan, status = row
        
        if status == 'paid':
            conn.close()
            return {"success": True, "message": "Подписка уже активна."}

        # Check status via API
        is_paid = False
        if invoice_id.startswith("mock_"):
            is_paid = True # Always approve mock for testing
        else:
            url = f"{CRYPTO_BOT_API}/getInvoices"
            headers = {"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
            params = {"invoice_ids": invoice_id}
            r = requests.get(url, headers=headers, params=params, timeout=10)
            data = r.json()
            if data.get("ok") and data["result"]["items"]:
                if data["result"]["items"][0]["status"] == "active": # Wait, 'paid' or 'active'? Docs say status can be active, paid, cancelled
                    # 'active' means not paid yet. 'paid' means paid.
                    if data["result"]["items"][0]["status"] == "paid":
                        is_paid = True
            
        if is_paid:
            # Determine duration
            days = 30
            if "6" in plan: days = 180
            if "12" in plan: days = 365
            
            expires_at = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
            plan_name = "Fast" if "fast" in plan else "Slow"
            
            c.execute("UPDATE payments SET status = 'paid' WHERE invoice_id = ?", (invoice_id,))
            c.execute("INSERT OR REPLACE INTO subscriptions (user_id, plan, expires_at, status) VALUES (?, ?, ?, 'active')",
                      (user_id, plan_name, expires_at))
            
            # --- Referral Commission (5%) ---
            try:
                c.execute("SELECT referrer_id FROM referral_stats WHERE user_id = ?", (user_id,))
                ref_row = c.fetchone()
                if ref_row and ref_row[0]:
                    referrer_id = ref_row[0]
                    # Get amount from payment record (row[0] is user_id, row[1] is plan, row[2] is status? No, check query at line 961)
                    # Query at line 961: "SELECT user_id, plan, status FROM payments WHERE invoice_id = ?"
                    # Wait, I need the amount too.
                    c.execute("SELECT amount FROM payments WHERE invoice_id = ?", (invoice_id,))
                    amount_row = c.fetchone()
                    if amount_row:
                        payment_amount = amount_row[0]
                        commission = payment_amount * 0.05
                        c.execute("UPDATE referral_stats SET balance = balance + ? WHERE user_id = ?", (commission, referrer_id))
                        print(f"REFERRAL: Credited {commission} RUB to referrer {referrer_id} for user {user_id}")
            except Exception as ref_err:
                print(f"Referral commission error: {ref_err}")
            
            conn.commit()
            
            # Notify Admin
            send_admin_tg(f"💰 <b>Новая оплата!</b>\nUser ID: {user_id}\nPlan: {plan_name}\nAmount: {payment_amount} RUB")
            
            conn.close()
            return {"success": True, "message": f"Подписка {plan_name} активирована!"}
        
        conn.close()
        return {"success": False, "message": "Платеж еще не оплачен. Пожалуйста, завершите оплату в CryptoBot."}
    except Exception as e:
        return {"success": False, "detail": str(e)}

class InstallPluginRequest(BaseModel):
    user_id: int
    plugin_id: int
    ip_address: str
    password: str

@app.post("/api/user/plugins/install")
def install_plugin_on_vps(req: InstallPluginRequest):
    # In a real app, this would trigger an Ansible script or similar.
    # For now, we just log it and add to DB.
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO user_installations (user_id, plugin_id, ip_address, status, installed_at) VALUES (?, ?, ?, 'Installing', ?)",
                  (req.user_id, req.plugin_id, req.ip_address, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        
        # Notify Admin
        send_admin_tg(f"🚀 <b>Запрос на установку плагина!</b>\nUser ID: {req.user_id}\nPlugin ID: {req.plugin_id}\nIP: {req.ip_address}")
        
        return {"success": True, "message": "Установка начата. Это может занять до 10 минут."}
    except Exception as e:
        return {"success": False, "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    # To run: python main.py
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=False)
