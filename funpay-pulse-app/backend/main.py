from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import hashlib

app = FastAPI(title="FunPayPulse API")

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
ADMIN_CHAT_ID = "755843448" 
BOT_TOKEN = '8997989380:AAFLk64Xrwe1ebr7LZMxaLuoDnT2Kg-P9-M'
FUNPAY_GOLDEN_KEY = "goomqs6ab8nho7areo9irc7cgorbc070"

import requests
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



# --- Endpoints ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "FunPayPulse API is running"}

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
            return {"success": True, "name": row[1], "user_id": row[2]}
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
        
        conn.close()
        
        return {
            "total_users": user_count,
            "total_sales": "42,300 руб.",
            "active_subs": 12,
            "total_plugins": plugin_count,
            "pending_support": 0
        }
    except Exception as e:
        if 'conn' in locals(): conn.close()
        return {"error": str(e)}

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

if __name__ == "__main__":
    import uvicorn
    # To run: python main.py
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=False)
