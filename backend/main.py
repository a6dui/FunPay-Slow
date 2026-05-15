import os
import secrets
import sqlite3
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Setup
DB_PATH = "funpay_slow.db"

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, first_name TEXT, username TEXT, plan TEXT, 
                  sub_end INTEGER, ref_code TEXT, referrer_id TEXT, balance REAL DEFAULT 0,
                  has_trial INTEGER DEFAULT 0, created_at INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS auth_tokens 
                 (token TEXT PRIMARY KEY, code TEXT, user_id TEXT, expires INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals_list 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id TEXT, user_id TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Auth Models ---
class AuthCheck(BaseModel):
    token: str

class UserUpdate(BaseModel):
    user_id: str
    first_name: Optional[str] = None
    username: Optional[str] = None

# --- ADMIN CHECK ---
def is_admin(user_id: str):
    # Твой ID и ID других админов
    admin_ids = ["6360699049", "5304677735", "755843448"]
    return str(user_id) in admin_ids

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "online", "version": "2.4.1"}

@app.get("/api/version")
def get_version():
    return {"version": "2.4.1"}

@app.get("/api/auth/generate")
def generate_auth():
    token = secrets.token_hex(16)
    code = str(secrets.randbelow(900000) + 100000)
    expires = int(time.time()) + 300 # 5 mins
    
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("INSERT INTO auth_tokens (token, code, expires) VALUES (?, ?, ?)", (token, code, expires))
    conn.commit()
    conn.close()
    
    return {"token": token, "code": code}

@app.get("/api/auth/check/{token}")
def check_auth(token: str):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM auth_tokens WHERE token = ? AND user_id IS NOT NULL", (token,))
    row = c.fetchone()
    
    if row:
        user_id = row[0]
        c.execute("SELECT user_id, first_name, username, plan FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        return {"user_id": user[0], "first_name": user[1], "username": user[2], "plan": user[3]}
    
    conn.close()
    raise HTTPException(status_code=404, detail="Not authorized yet")

@app.get("/api/user/subscription/{user_id}")
def get_subscription(user_id: str):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT plan, sub_end, has_trial, created_at FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "plan": row[0], 
            "expires": row[1], 
            "has_trial": bool(row[2]),
            "created_at": row[3]
        }
    return {"plan": "none", "expires": 0, "has_trial": False, "created_at": 0}

@app.post("/api/subscription/trial")
def activate_trial(user_id: str):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT has_trial, plan FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    if row[0] == 1 or row[1] != "none":
        conn.close()
        raise HTTPException(status_code=400, detail="Trial already used or active subscription")
    
    # Activate 4 days trial (Slow plan by default for trial)
    sub_end = int(time.time()) + (4 * 24 * 3600)
    c.execute("UPDATE users SET plan = 'slow', sub_end = ?, has_trial = 1 WHERE user_id = ?", (sub_end, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "expires": sub_end}

class PaymentRequest(BaseModel):
    user_id: str
    plan_type: str # fast_1m, slow_6m
    price: float

@app.post("/api/payment/create")
def create_payment(data: PaymentRequest):
    # This is a placeholder for Crypto Bot API or a simple bot link
    # For now we return a deep link to the bot
    amount = data.price
    payload = f"sub_{data.plan_type}_{data.user_id}"
    bot_url = f"https://t.me/CryptoBot?start=pay_{amount}_USD" # Example
    return {"payment_url": bot_url}

@app.get("/api/admin/stats")
def get_admin_stats(admin_id: str):
    if not is_admin(admin_id):
        raise HTTPException(status_code=403, detail="Forbidden")
        
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE plan = 'fast'")
    fast_users = c.fetchone()[0]
    conn.close()
    
    return {
        "total_users": total_users,
        "active_fast": fast_users,
        "revenue_estimated": fast_users * 15, # Example
        "system_status": "healthy"
    }

# --- Telegram Bot Webhook Logic (Placeholder) ---
# В реальной жизни здесь будет обработка обновлений от бота
@app.post("/api/bot/auth-confirm")
def bot_confirm(code: str, user_id: str, first_name: str, username: str):
    conn = get_db_conn()
    c = conn.cursor()
    
    # Update auth token
    c.execute("UPDATE auth_tokens SET user_id = ? WHERE code = ?", (user_id, code))
    
    # Create or update user
    now = int(time.time())
    c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, plan, created_at) VALUES (?, ?, ?, 'none', ?)", 
              (user_id, first_name, username, now))
    
    conn.commit()
    conn.close()
    return {"status": "success"}

class ReportData(BaseModel):
    user_id: str
    username: str
    message: str

@app.post("/api/report/send")
def send_report(data: ReportData):
    # Здесь логика отправки сообщения в Telegram Bot
    # Для теста просто логируем и возвращаем успех
    print(f"REPORT from {data.username} ({data.user_id}): {data.message}")
    return {"status": "success", "detail": "Report received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
