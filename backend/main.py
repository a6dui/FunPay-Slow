import os
import secrets
import sqlite3
import time
import threading
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "funpay_slow.db")

CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "581922:AA78JPxCzqnhyX8n6tyzrTJysjB4zbpFC9q")
CRYPTO_PAY_URL   = "https://pay.crypt.bot/api"

BOT_TOKEN = os.getenv("BOT_TOKEN", "")   # Set in Render environment variables
ADMIN_IDS = ["6360699049", "5304677735", "755843448"]

import httpx

# ─── Database ─────────────────────────────────────────────────────────────────
def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   TEXT PRIMARY KEY,
            first_name TEXT,
            username  TEXT,
            plan      TEXT DEFAULT 'none',
            sub_end   INTEGER DEFAULT 0,
            ref_code  TEXT,
            referrer_id TEXT,
            balance   REAL DEFAULT 0,
            has_trial INTEGER DEFAULT 0,
            created_at INTEGER,
            is_banned INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS auth_tokens (
            token   TEXT PRIMARY KEY,
            code    TEXT,
            user_id TEXT,
            expires INTEGER
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   TEXT,
            name      TEXT,
            cookie    TEXT,
            proxy     TEXT,
            is_active INTEGER DEFAULT 1,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS referrals_list (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id TEXT,
            user_id     TEXT,
            created_at  TEXT
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ─── Helpers ──────────────────────────────────────────────────────────────────
def is_admin(user_id: str) -> bool:
    return str(user_id) in ADMIN_IDS

def user_row_to_dict(row) -> dict:
    """Convert a sqlite3.Row user record to a clean API dict."""
    if not row:
        return {}
    plan = (row["plan"] or "none").upper()
    return {
        "user_id":    row["user_id"],
        "first_name": row["first_name"],
        "username":   row["username"],
        "plan":       plan,
        "sub_end":    row["sub_end"] or 0,
        "balance":    round(float(row["balance"] or 0), 2),
        "ref_code":   row["ref_code"] or "",
        "has_trial":  bool(row["has_trial"]),
        "created_at": row["created_at"] or 0,
        "is_banned":  bool(row["is_banned"]),
    }

# ─── Pydantic Models ──────────────────────────────────────────────────────────
class TrialRequest(BaseModel):
    user_id: str

class PaymentRequest(BaseModel):
    user_id: str
    plan_type: str
    price: float

class AdminUserAction(BaseModel):
    admin_id: str
    target_user_id: str
    action: str  # ban | unban | set_sub | update_balance
    plan: Optional[str] = "none"
    duration_days: Optional[int] = 0
    balance_delta: Optional[float] = 0

class AccountAdd(BaseModel):
    user_id: str
    name: str
    cookie: str
    proxy: Optional[str] = ""

# ─── Root ──────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "online", "version": "2.5.0"}

@app.get("/api/version")
def get_version():
    return {"version": "2.5.0"}

# ─── Auth ──────────────────────────────────────────────────────────────────────
@app.get("/api/auth/generate")
def generate_auth():
    token = secrets.token_hex(16)
    code  = str(secrets.randbelow(900000) + 100000)
    expires = int(time.time()) + 300
    conn = get_db_conn()
    conn.execute("INSERT INTO auth_tokens (token, code, expires) VALUES (?, ?, ?)", (token, code, expires))
    conn.commit()
    conn.close()
    return {"token": token, "code": code}

@app.get("/api/auth/check/{token}")
def check_auth(token: str):
    conn = get_db_conn()
    row = conn.execute(
        "SELECT user_id FROM auth_tokens WHERE token = ? AND user_id IS NOT NULL AND expires > ?",
        (token, int(time.time()))
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Not authorized yet")

    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (row["user_id"],)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["is_banned"]:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован.")
    return user_row_to_dict(user)

# Called by the Telegram bot when user sends /start <code>
@app.post("/api/bot/auth-confirm")
def bot_confirm(code: str, user_id: str, first_name: str = "", username: str = ""):
    now = int(time.time())
    conn = get_db_conn()
    conn.execute("UPDATE auth_tokens SET user_id = ? WHERE code = ? AND expires > ?", (user_id, code, now))
    ref_code = secrets.token_hex(4).upper()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, first_name, username, plan, ref_code, created_at) VALUES (?, ?, ?, 'none', ?, ?)",
        (user_id, first_name, username, ref_code, now)
    )
    # Update name in case it changed
    conn.execute("UPDATE users SET first_name = ?, username = ? WHERE user_id = ?", (first_name, username, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

# ─── User / Subscription ───────────────────────────────────────────────────────
@app.get("/api/user/subscription/{user_id}")
def get_subscription(user_id: str):
    conn = get_db_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return {"plan": "NONE", "sub_end": 0, "has_trial": False, "balance": 0, "ref_code": ""}
    return user_row_to_dict(row)

@app.post("/api/user/activate-trial")
def activate_trial(data: TrialRequest):
    conn = get_db_conn()
    row = conn.execute("SELECT has_trial, plan FROM users WHERE user_id = ?", (data.user_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    if row["has_trial"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Вы уже использовали пробный период.")
    plan = (row["plan"] or "none").lower()
    if plan not in ("none", ""):
        conn.close()
        raise HTTPException(status_code=400, detail="У вас уже есть активная подписка.")

    sub_end = int(time.time()) + 4 * 24 * 3600
    conn.execute("UPDATE users SET plan = 'FAST', sub_end = ?, has_trial = 1 WHERE user_id = ?", (sub_end, data.user_id))
    conn.commit()
    conn.close()
    return {"status": "success", "plan": "FAST", "sub_end": sub_end}

# ─── Accounts ─────────────────────────────────────────────────────────────────
@app.post("/api/accounts/add")
def add_account(data: AccountAdd):
    conn = get_db_conn()
    conn.execute(
        "INSERT INTO accounts (user_id, name, cookie, proxy, is_active, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        (data.user_id, data.name, data.cookie, data.proxy, int(time.time()))
    )
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/accounts/list")
def list_accounts(user_id: str):
    conn = get_db_conn()
    rows = conn.execute(
        "SELECT id, name, proxy, is_active FROM accounts WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "name": r["name"], "proxy": r["proxy"], "is_active": bool(r["is_active"])} for r in rows]

@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int, user_id: str):
    conn = get_db_conn()
    conn.execute("DELETE FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
    conn.commit()
    conn.close()
    return {"status": "deleted"}

# ─── Payments ─────────────────────────────────────────────────────────────────
def _days_from_plan(plan_type: str) -> int:
    if "12m" in plan_type: return 365
    if "6m"  in plan_type: return 180
    if "3m"  in plan_type: return 90
    return 30

def _tier_from_plan(plan_type: str) -> str:
    return "SLOW" if "slow" in plan_type.lower() else "FAST"

@app.post("/api/payment/create")
async def create_payment(data: PaymentRequest):
    plan_names = {
        "slow_1m":"SLOW (1 мес.)", "slow_3m":"SLOW (3 мес.)", "slow_6m":"SLOW (6 мес.)", "slow_12m":"SLOW (12 мес.)",
        "fast_1m":"FAST (1 мес.)", "fast_3m":"FAST (3 мес.)", "fast_6m":"FAST (6 мес.)", "fast_12m":"FAST (12 мес.)",
    }
    payload_str = f"{data.user_id}|{data.plan_type}|{data.price}"
    body = {
        "asset": "USDT",
        "amount": str(data.price),
        "currency_type": "fiat",
        "fiat": "RUB",
        "description": f"FunPay Slow: {plan_names.get(data.plan_type, data.plan_type)}",
        "payload": payload_str,
        "allow_comments": False,
        "allow_anonymous": False,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CRYPTO_PAY_URL}/createInvoice",
            json=body,
            headers={"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
        )
    res = resp.json()
    if res.get("ok"):
        return {"payment_url": res["result"]["pay_url"]}
    raise HTTPException(status_code=500, detail=str(res))

@app.post("/api/payment/pay-with-balance")
def pay_with_balance(data: PaymentRequest):
    conn = get_db_conn()
    row = conn.execute("SELECT balance FROM users WHERE user_id = ?", (data.user_id,)).fetchone()
    if not row or float(row["balance"]) < data.price:
        conn.close()
        raise HTTPException(status_code=400, detail="Недостаточно средств на балансе.")
    days = _days_from_plan(data.plan_type)
    tier = _tier_from_plan(data.plan_type)
    sub_end = int(time.time()) + days * 86400
    conn.execute(
        "UPDATE users SET balance = balance - ?, plan = ?, sub_end = ? WHERE user_id = ?",
        (data.price, tier, sub_end, data.user_id)
    )
    conn.commit()
    # Return updated user
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (data.user_id,)).fetchone()
    conn.close()
    return {"status": "success", "user": user_row_to_dict(user)}

@app.post("/api/payment/webhook")
async def crypto_webhook(request: Request):
    data = await request.json()
    if data.get("update_type") != "invoice_paid":
        return {"ok": True}
    payload_str = data.get("payload", {}).get("payload", "")
    parts = payload_str.split("|")
    if len(parts) < 3:
        return {"ok": True, "detail": "bad payload"}
    u_id, p_type, price_str = parts[0], parts[1], parts[2]
    price = float(price_str)
    days = _days_from_plan(p_type)
    tier = _tier_from_plan(p_type)
    sub_end = int(time.time()) + days * 86400
    conn = get_db_conn()
    conn.execute("UPDATE users SET plan = ?, sub_end = ? WHERE user_id = ?", (tier, sub_end, u_id))
    ref_row = conn.execute("SELECT referrer_id FROM users WHERE user_id = ?", (u_id,)).fetchone()
    if ref_row and ref_row["referrer_id"]:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (price * 0.05, ref_row["referrer_id"]))
    conn.commit()
    conn.close()
    return {"ok": True}

# ─── Admin ────────────────────────────────────────────────────────────────────
@app.get("/api/admin/stats")
def admin_stats(admin_id: str):
    if not is_admin(admin_id):
        raise HTTPException(status_code=403)
    conn = get_db_conn()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    fast  = conn.execute("SELECT COUNT(*) FROM users WHERE UPPER(plan)='FAST'").fetchone()[0]
    slow  = conn.execute("SELECT COUNT(*) FROM users WHERE UPPER(plan)='SLOW'").fetchone()[0]
    conn.close()
    return {"total_users": total, "active_fast": fast, "active_slow": slow, "system_status": "healthy"}

@app.get("/api/admin/users")
def admin_users(admin_id: str):
    if not is_admin(admin_id):
        raise HTTPException(status_code=403)
    conn = get_db_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [user_row_to_dict(r) for r in rows]

@app.post("/api/admin/user/action")
def admin_action(data: AdminUserAction):
    if not is_admin(data.admin_id):
        raise HTTPException(status_code=403)
    conn = get_db_conn()
    if data.action == "ban":
        conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (data.target_user_id,))
    elif data.action == "unban":
        conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (data.target_user_id,))
    elif data.action == "set_sub":
        sub_end = int(time.time()) + data.duration_days * 86400 if data.duration_days else 0
        plan = (data.plan or "none").upper()
        conn.execute("UPDATE users SET plan = ?, sub_end = ? WHERE user_id = ?", (plan, sub_end, data.target_user_id))
    elif data.action == "update_balance":
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (data.balance_delta, data.target_user_id))
    conn.commit()
    # Return updated user data so frontend can refresh
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (data.target_user_id,)).fetchone()
    conn.close()
    return {"status": "success", "user": user_row_to_dict(user) if user else {}}

# ─── Telegram Bot ─────────────────────────────────────────────────────────────
if BOT_TOKEN:
    try:
        import telebot
        bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

        @bot.message_handler(commands=["start"])
        def handle_start(message):
            args = message.text.split()
            user_id    = str(message.from_user.id)
            first_name = message.from_user.first_name or ""
            username   = message.from_user.username or ""

            if len(args) > 1:
                code = args[1]
                # Confirm auth via internal API
                now = int(time.time())
                conn = get_db_conn()
                conn.execute("UPDATE auth_tokens SET user_id = ? WHERE code = ? AND expires > ?", (user_id, code, now))
                ref_code = secrets.token_hex(4).upper()
                conn.execute(
                    "INSERT OR IGNORE INTO users (user_id, first_name, username, plan, ref_code, created_at) VALUES (?, ?, ?, 'none', ?, ?)",
                    (user_id, first_name, username, ref_code, now)
                )
                conn.execute("UPDATE users SET first_name = ?, username = ? WHERE user_id = ?", (first_name, username, user_id))
                conn.commit()
                conn.close()
                bot.send_message(
                    message.chat.id,
                    f"✅ <b>Авторизация успешна!</b>\n\nДобро пожаловать, <b>{first_name}</b>!\nВернитесь на сайт — страница обновится автоматически."
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "👋 <b>FunPay Slow Bot</b>\n\nДля входа на сайт нажмите кнопку <b>«Войти через Telegram»</b> и отсканируйте код."
                )

        @bot.message_handler(commands=["status"])
        def handle_status(message):
            user_id = str(message.from_user.id)
            conn = get_db_conn()
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            conn.close()
            if not row:
                bot.send_message(message.chat.id, "❌ Вы не зарегистрированы. Войдите через сайт.")
                return
            u = user_row_to_dict(row)
            plan = u["plan"]
            bal  = u["balance"]
            if u["sub_end"] > 0:
                days = max(0, (u["sub_end"] - int(time.time())) // 86400)
                exp  = f"осталось {days} дн."
            else:
                exp = "нет подписки"
            bot.send_message(
                message.chat.id,
                f"📊 <b>Ваш статус</b>\n\n"
                f"🎫 План: <b>{plan}</b>\n"
                f"⏱ Подписка: <b>{exp}</b>\n"
                f"💰 Баланс: <b>{bal} ₽</b>"
            )

        def _run_bot():
            print("✅ Bot polling started")
            bot.remove_webhook()
            while True:
                try:
                    bot.infinity_polling(timeout=60, long_polling_timeout=30)
                except Exception as e:
                    print(f"Bot crashed, restarting in 5s: {e}")
                    time.sleep(5)

        threading.Thread(target=_run_bot, daemon=True).start()
        print("✅ Telegram bot thread launched")
    except Exception as e:
        print(f"⚠️ Bot init failed: {e}")
else:
    print("⚠️ BOT_TOKEN not set — bot disabled")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
