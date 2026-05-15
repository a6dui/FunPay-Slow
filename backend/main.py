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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "funpay_slow.db")

# Crypto Bot API Token
CRYPTO_BOT_TOKEN = "581922:AA78JPxCzqnhyX8n6tyzrTJysjB4zbpFC9q"
CRYPTO_PAY_URL = "https://pay.cryptobot.pay/api" # Mainnet

import httpx # Ensure httpx is used for async requests

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, first_name TEXT, username TEXT, plan TEXT, 
                  sub_end INTEGER, ref_code TEXT, referrer_id TEXT, balance REAL DEFAULT 0,
                  has_trial INTEGER DEFAULT 0, created_at INTEGER, is_banned INTEGER DEFAULT 0)''')
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
        c.execute("SELECT user_id, first_name, username, plan, balance, ref_code, is_banned FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        
        if user[6] == 1:
            raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован.")
            
        return {
            "user_id": user[0], 
            "first_name": user[1], 
            "username": user[2], 
            "plan": user[3],
            "balance": user[4],
            "ref_code": user[5]
        }
    
    conn.close()
    raise HTTPException(status_code=404, detail="Not authorized yet")

@app.get("/api/user/subscription/{user_id}")
def get_subscription(user_id: str):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT plan, sub_end, has_trial, balance, ref_code FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {
            "plan": row[0], 
            "expires": row[1], 
            "has_trial": bool(row[2]),
            "balance": row[3],
            "ref_code": row[4]
        }
    return {"plan": "none", "expires": 0, "has_trial": False, "balance": 0, "ref_code": ""}

class TrialRequest(BaseModel):
    user_id: str
    plan: Optional[str] = "FAST"

@app.post("/api/user/activate-trial")
def activate_trial(data: TrialRequest):
    user_id = data.user_id
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT has_trial, plan FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if not row:
        # Create user if doesn't exist (e.g. first login via trial)
        now = int(time.time())
        c.execute("INSERT INTO users (user_id, plan, has_trial, created_at) VALUES (?, 'none', 0, ?)", (user_id, now))
        row = (0, "none")
    
    if row[0] == 1:
        conn.close()
        raise HTTPException(status_code=400, detail="Вы уже использовали пробный период.")
    
    if row[1] != "none" and row[1] is not None:
        conn.close()
        raise HTTPException(status_code=400, detail="У вас уже есть активная подписка.")
    
    # Activate 4 days trial (FAST plan)
    sub_end = int(time.time()) + (4 * 24 * 3600)
    c.execute("UPDATE users SET plan = 'FAST', sub_end = ?, has_trial = 1 WHERE user_id = ?", (sub_end, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "expires": sub_end, "plan": "FAST"}

class PaymentRequest(BaseModel):
    user_id: str
    plan_type: str # fast_1m, slow_6m
    price: float

@app.post("/api/payment/create")
async def create_payment(data: PaymentRequest):
    # Create Invoice via Crypto Bot API
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN
    }
    
    plan_names = {
        "slow_1m": "SLOW (1 месяц)", "slow_3m": "SLOW (3 месяца)", "slow_6m": "SLOW (6 месяцев)", "slow_12m": "SLOW (12 месяцев)",
        "fast_1m": "FAST (1 месяц)", "fast_3m": "FAST (3 месяца)", "fast_6m": "FAST (6 месяцев)", "fast_12m": "FAST (12 месяцев)"
    }
    
    description = f"Подписка FunPay Slow: {plan_names.get(data.plan_type, data.plan_type)}"
    
    payload = {
        "asset": "USDT", 
        "amount": str(data.price), 
        "currency_type": "fiat",
        "fiat": "RUB",
        "description": description,
        "payload": f"pay_{data.plan_type}_{data.user_id}",
        "allow_comments": False,
        "allow_anonymous": False
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{CRYPTO_PAY_URL}/createInvoice", json=payload, headers=headers)
            res_data = resp.json()
            if res_data.get("ok"):
                return {"payment_url": res_data["result"]["pay_url"]}
            else:
                raise HTTPException(status_code=500, detail="Ошибка Crypto Bot")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Ошибка связи")

@app.post("/api/payment/webhook")
async def crypto_bot_webhook(request: Request):
    # Verify signature would go here (omitted for simplicity but recommended)
    data = await request.json()
    
    if data.get("update_type") == "invoice_paid":
        payload_str = data["payload"]["payload"] # Format: pay_planId_userId
        if not payload_str.startswith("pay_"):
            return {"status": "ignored"}
            
        parts = payload_str.split("_")
        if len(parts) < 3:
            return {"status": "error"}
            
        plan_id = f"{parts[1]}_{parts[2]}" # slow_1m
        user_id = parts[3]
        amount_rub = float(data["payload"]["fiat_amount"]) if "fiat_amount" in data["payload"] else 0
        
        # Determine duration and plan tier
        duration_days = 30
        if "3m" in plan_id: duration_days = 90
        elif "6m" in plan_id: duration_days = 180
        elif "12m" in plan_id: duration_days = 365
        
        plan_tier = "SLOW" if "slow" in plan_id else "FAST"
        
        conn = get_db_conn()
        c = conn.cursor()
        
        # 1. Activate Subscription
        now = int(time.time())
        sub_end = now + (duration_days * 24 * 3600)
        c.execute("UPDATE users SET plan = ?, sub_end = ? WHERE user_id = ?", (plan_tier, sub_end, user_id))
        
        # 2. Handle Referrals (5% reward)
        c.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
        ref_row = c.fetchone()
        if ref_row and ref_row[0]:
            referrer_id = ref_row[0]
            reward = amount_rub * 0.05
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, referrer_id))
            print(f"Referral reward: {reward} RUB sent to {referrer_id}")
            
        conn.commit()
        conn.close()
        print(f"Payment Confirmed: User {user_id} activated {plan_tier} for {duration_days} days.")
        
    return {"ok": True}

@app.post("/api/payment/pay-with-balance")
def pay_with_balance(data: PaymentRequest):
    user_id = data.user_id
    plan_id = data.plan_type
    price = data.price
    
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT balance, plan FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if not row or row[0] < price:
        conn.close()
        raise HTTPException(status_code=400, detail="Недостаточно средств на балансе.")
        
    # Deduct balance
    new_balance = row[0] - price
    
    # Determine duration
    duration_days = 30
    if "3m" in plan_id: duration_days = 90
    elif "6m" in plan_id: duration_days = 180
    elif "12m" in plan_id: duration_days = 365
    
    plan_tier = "SLOW" if "slow" in plan_id else "FAST"
    
    now = int(time.time())
    sub_end = now + (duration_days * 24 * 3600)
    
    c.execute("UPDATE users SET balance = ?, plan = ?, sub_end = ? WHERE user_id = ?", 
              (new_balance, plan_tier, sub_end, user_id))
    
    conn.commit()
    conn.close()
    return {"status": "success", "new_balance": new_balance}

# --- Telegram Bot Webhook Logic (Placeholder) ---

@app.get("/api/admin/users")
def list_users(admin_id: str):
    if not is_admin(admin_id): raise HTTPException(status_code=403)
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, plan, sub_end, balance, is_banned FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"user_id": r[0], "first_name": r[1], "username": r[2], "plan": r[3], "sub_end": r[4], "balance": r[5], "is_banned": r[6]} for r in rows]

class AdminUserAction(BaseModel):
    admin_id: str
    target_user_id: str
    action: str # ban, unban, set_sub, update_balance
    plan: Optional[str] = "none"
    duration_days: Optional[int] = 0
    balance_delta: Optional[float] = 0

@app.post("/api/admin/user/action")
def admin_user_action(data: AdminUserAction):
    if not is_admin(data.admin_id): raise HTTPException(status_code=403)
    conn = get_db_conn()
    c = conn.cursor()
    
    if data.action == "ban":
        c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (data.target_user_id,))
    elif data.action == "unban":
        c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (data.target_user_id,))
    elif data.action == "set_sub":
        sub_end = int(time.time()) + (data.duration_days * 24 * 3600) if data.duration_days > 0 else 0
        c.execute("UPDATE users SET plan = ?, sub_end = ? WHERE user_id = ?", (data.plan, sub_end, data.target_user_id))
    elif data.action == "update_balance":
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (data.balance_delta, data.target_user_id))
        
    conn.commit()
    conn.close()
    return {"status": "success"}

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

@app.post("/api/user/activate-trial")
def activate_trial(data: dict):
    user_id = data.get("user_id")
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT has_trial FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row: raise HTTPException(status_code=404, detail="User not found")
    if row[0] == 1: raise HTTPException(status_code=400, detail="Trial already used")
    
    sub_end = int(time.time()) + (4 * 24 * 3600)
    c.execute("UPDATE users SET plan = 'FAST', sub_end = ?, has_trial = 1 WHERE user_id = ?", (sub_end, user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "detail": "Trial activated"}

@app.post("/api/accounts/add")
def add_account(data: dict):
    user_id = data.get("user_id")
    name = data.get("name")
    cookie = data.get("cookie")
    proxy = data.get("proxy", "")
    
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("INSERT INTO accounts (user_id, name, cookie, proxy, is_active) VALUES (?, ?, ?, ?, 1)", 
              (user_id, name, cookie, proxy))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/accounts/list")
def list_accounts(user_id: str):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT name, is_active, proxy FROM accounts WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"name": r[0], "is_active": r[1], "proxy": r[2]} for r in rows]

@app.post("/api/payment/pay-with-balance")
def pay_with_balance(data: dict):
    user_id = data.get("user_id")
    plan_type = data.get("plan_type") # e.g. slow_1m
    price = data.get("price")
    
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = c.fetchone()[0]
    
    if balance < price:
        conn.close()
        raise HTTPException(status_code=400, detail="Insufficient balance")
        
    days = 30
    if "_3m" in plan_type: days = 90
    elif "_6m" in plan_type: days = 180
    elif "_12m" in plan_type: days = 365
    
    plan_base = "SLOW" if "slow" in plan_type else "FAST"
    sub_end = int(time.time()) + (days * 24 * 3600)
    
    c.execute("UPDATE users SET balance = balance - ?, plan = ?, sub_end = ? WHERE user_id = ?", 
              (price, plan_base, sub_end, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/payment/webhook")
async def crypto_bot_webhook(request: Request):
    # This is a simple webhook for Crypto Bot
    # In production, check for HMAC or IP whitelist
    data = await request.json()
    if data.get("status") == "paid" or (data.get("update_type") == "invoice_paid"):
        payload = data.get("payload") or data.get("invoice", {}).get("payload")
        if not payload: return {"status": "ignored"}
        
        # Payload format: "user_id|plan_type|price"
        parts = payload.split("|")
        if len(parts) < 3: return {"status": "error"}
        
        u_id, p_type, price = parts[0], parts[1], float(parts[2])
        
        days = 30
        if "_3m" in p_type: days = 90
        elif "_6m" in p_type: days = 180
        elif "_12m" in p_type: days = 365
        
        plan_base = "SLOW" if "slow" in p_type else "FAST"
        sub_end = int(time.time()) + (days * 24 * 3600)
        
        conn = get_db_conn()
        c = conn.cursor()
        c.execute("UPDATE users SET plan = ?, sub_end = ? WHERE user_id = ?", (plan_base, sub_end, u_id))
        
        # Referral reward (5%)
        c.execute("SELECT referrer_id FROM users WHERE user_id = ?", (u_id,))
        ref_id = c.fetchone()[0]
        if ref_id:
            reward = price * 0.05
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, ref_id))
            
        conn.commit()
        conn.close()
        
    return {"status": "ok"}

# Start Bot Thread
import threading
def run_bot():
    try:
        print("Starting Telegram Bot Polling...")
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot Error: {e}")

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
