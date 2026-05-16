import os
import secrets
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
DATABASE_URL     = os.getenv("DATABASE_URL", "")       # PostgreSQL on Render
BOT_TOKEN        = os.getenv("BOT_TOKEN", "8997989380:AAFLk64Xrwe1ebr7LZMxaLuoDnT2Kg-P9-M")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN", "581922:AA78JPxCzqnhyX8n6tyzrTJysjB4zbpFC9q")
CRYPTO_PAY_URL   = "https://pay.crypt.bot/api"
ADMIN_IDS        = ["6360699049", "5304677735", "755843448"]
BOT_USERNAME     = os.getenv("BOT_USERNAME", "FunPaySlov_Bot")

import httpx

# ─── Database (PostgreSQL via psycopg2 / fallback SQLite) ─────────────────────
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
        print("✅ psycopg2 loaded — using PostgreSQL")
    except ImportError:
        print("⚠️ psycopg2 not found — falling back to SQLite")
        USE_POSTGRES = False

if USE_POSTGRES:
    def get_db_conn():
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(url)
        conn.autocommit = False
        return conn

    def _ph():
        return "%s"
else:
    import sqlite3
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH  = os.path.join(BASE_DIR, "funpay_slow.db")

    def get_db_conn():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _ph():
        return "?"


def _row_to_dict(row) -> dict:
    if USE_POSTGRES:
        return dict(row) if row else {}
    else:
        return dict(row) if row else {}


def init_db():
    conn = get_db_conn()
    c = conn.cursor()

    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     TEXT PRIMARY KEY,
                first_name  TEXT,
                username    TEXT,
                plan        TEXT DEFAULT 'none',
                sub_end     BIGINT DEFAULT 0,
                ref_code    TEXT,
                referrer_id TEXT,
                balance     FLOAT DEFAULT 0,
                has_trial   INTEGER DEFAULT 0,
                created_at  BIGINT,
                is_banned   INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token   TEXT PRIMARY KEY,
                code    TEXT,
                user_id TEXT,
                expires BIGINT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id         SERIAL PRIMARY KEY,
                user_id    TEXT,
                name       TEXT,
                cookie     TEXT,
                proxy      TEXT,
                is_active  INTEGER DEFAULT 1,
                created_at BIGINT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS referrals_list (
                id          SERIAL PRIMARY KEY,
                referrer_id TEXT,
                user_id     TEXT,
                created_at  TEXT
            )
        """)
        conn.commit()
    else:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY, first_name TEXT, username TEXT,
                plan TEXT DEFAULT 'none', sub_end INTEGER DEFAULT 0,
                ref_code TEXT, referrer_id TEXT, balance REAL DEFAULT 0,
                has_trial INTEGER DEFAULT 0, created_at INTEGER, is_banned INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY, code TEXT, user_id TEXT, expires INTEGER
            );
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, name TEXT,
                cookie TEXT, proxy TEXT, is_active INTEGER DEFAULT 1, created_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS referrals_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id TEXT, user_id TEXT, created_at TEXT
            );
        """)
        conn.commit()

    conn.close()

init_db()
print(f"✅ DB initialized ({'PostgreSQL' if USE_POSTGRES else 'SQLite'})")


# ─── Helpers ──────────────────────────────────────────────────────────────────
def is_admin(uid: str) -> bool:
    return str(uid) in ADMIN_IDS


def user_to_api(row: dict) -> dict:
    if not row:
        return {}
    plan = (row.get("plan") or "none").upper()
    return {
        "user_id":    str(row.get("user_id", "")),
        "first_name": row.get("first_name") or "",
        "username":   row.get("username") or "",
        "plan":       plan,
        "sub_end":    int(row.get("sub_end") or 0),
        "balance":    round(float(row.get("balance") or 0), 2),
        "ref_code":   row.get("ref_code") or "",
        "has_trial":  bool(row.get("has_trial")),
        "created_at": int(row.get("created_at") or 0),
        "is_banned":  bool(row.get("is_banned")),
    }


def fetchone(conn, sql: str, params: tuple = ()) -> dict:
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute(sql, params)
        row = c.fetchone()
        if row is None:
            return {}
        cols = [d[0] for d in c.description]
        return dict(zip(cols, row))
    else:
        c.execute(sql, params)
        row = c.fetchone()
        return dict(row) if row else {}


def fetchall(conn, sql: str, params: tuple = ()) -> list:
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute(sql, params)
        rows = c.fetchall()
        cols = [d[0] for d in c.description]
        return [dict(zip(cols, r)) for r in rows]
    else:
        c.execute(sql, params)
        return [dict(r) for r in c.fetchall()]


def execute(conn, sql: str, params: tuple = ()):
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()


P = _ph()  # placeholder: ? or %s


# ─── Pydantic ─────────────────────────────────────────────────────────────────
class TrialRequest(BaseModel):
    user_id: str

class PaymentRequest(BaseModel):
    user_id: str
    plan_type: str
    price: float

class AdminUserAction(BaseModel):
    admin_id: str
    target_user_id: str
    action: str
    plan: Optional[str] = "none"
    duration_days: Optional[int] = 0
    balance_delta: Optional[float] = 0

class AccountAdd(BaseModel):
    user_id: str
    name: str
    cookie: str
    proxy: Optional[str] = ""


# ─── Root ─────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "online", "version": "2.6.0", "db": "postgres" if USE_POSTGRES else "sqlite"}


@app.get("/api/version")
def version():
    return {"version": "2.6.0"}


# ─── Auth ──────────────────────────────────────────────────────────────────────
@app.get("/api/auth/generate")
def generate_auth():
    token = secrets.token_hex(16)
    code  = str(secrets.randbelow(900000) + 100000)
    exp   = int(time.time()) + 300
    conn  = get_db_conn()
    execute(conn, f"INSERT INTO auth_tokens (token, code, expires) VALUES ({P}, {P}, {P})", (token, code, exp))
    conn.close()
    return {"token": token, "code": code}


@app.get("/api/auth/check/{token}")
def check_auth(token: str):
    conn = get_db_conn()
    tr = fetchone(conn, f"SELECT user_id FROM auth_tokens WHERE token = {P} AND user_id IS NOT NULL AND expires > {P}", (token, int(time.time())))
    if not tr:
        conn.close()
        raise HTTPException(status_code=404, detail="Not authorized yet")
    user = fetchone(conn, f"SELECT * FROM users WHERE user_id = {P}", (tr["user_id"],))
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован.")
    return user_to_api(user)


@app.post("/api/bot/auth-confirm")
def bot_auth_confirm(code: str, user_id: str, first_name: str = "", username: str = ""):
    """Called by Telegram bot when user sends the code."""
    now  = int(time.time())
    conn = get_db_conn()
    execute(conn, f"UPDATE auth_tokens SET user_id = {P} WHERE code = {P} AND expires > {P}", (user_id, code, now))
    ref_code = secrets.token_hex(4).upper()
    execute(conn,
        f"INSERT INTO users (user_id, first_name, username, plan, ref_code, created_at) VALUES ({P},{P},{P},'none',{P},{P}) "
        f"ON CONFLICT (user_id) DO UPDATE SET first_name={P}, username={P}",
        (user_id, first_name, username, ref_code, now, first_name, username)
        if USE_POSTGRES else
        (user_id, first_name, username, ref_code, now)
    )
    if not USE_POSTGRES:
        # SQLite fallback: update name separately
        execute(conn, f"UPDATE users SET first_name={P}, username={P} WHERE user_id={P}", (first_name, username, user_id))
    conn.close()
    return {"status": "success"}


# ─── User / Subscription ───────────────────────────────────────────────────────
@app.get("/api/user/subscription/{user_id}")
def get_sub(user_id: str):
    conn = get_db_conn()
    row  = fetchone(conn, f"SELECT * FROM users WHERE user_id = {P}", (user_id,))
    conn.close()
    if not row:
        return {"plan": "NONE", "sub_end": 0, "has_trial": False, "balance": 0, "ref_code": ""}
    return user_to_api(row)


@app.post("/api/user/activate-trial")
def activate_trial(data: TrialRequest):
    conn = get_db_conn()
    row = fetchone(conn, f"SELECT has_trial, plan FROM users WHERE user_id = {P}", (data.user_id,))
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    if row.get("has_trial"):
        conn.close()
        raise HTTPException(status_code=400, detail="Вы уже использовали пробный период.")
    plan = (row.get("plan") or "none").lower()
    if plan not in ("none", ""):
        conn.close()
        raise HTTPException(status_code=400, detail="У вас уже есть активная подписка.")
    sub_end = int(time.time()) + 4 * 86400
    execute(conn, f"UPDATE users SET plan='FAST', sub_end={P}, has_trial=1 WHERE user_id={P}", (sub_end, data.user_id))
    conn.close()
    return {"status": "success", "plan": "FAST", "sub_end": sub_end}


# ─── Accounts ─────────────────────────────────────────────────────────────────
@app.post("/api/accounts/add")
def add_account(data: AccountAdd):
    conn = get_db_conn()
    execute(conn,
        f"INSERT INTO accounts (user_id, name, cookie, proxy, is_active, created_at) VALUES ({P},{P},{P},{P},1,{P})",
        (data.user_id, data.name, data.cookie, data.proxy, int(time.time()))
    )
    conn.close()
    return {"status": "success"}


@app.get("/api/accounts/list")
def list_accounts(user_id: str):
    conn = get_db_conn()
    rows = fetchall(conn, f"SELECT id, name, proxy, is_active FROM accounts WHERE user_id = {P} ORDER BY id DESC", (user_id,))
    conn.close()
    return [{"id": r["id"], "name": r["name"], "proxy": r.get("proxy", ""), "is_active": bool(r["is_active"])} for r in rows]


@app.delete("/api/accounts/{account_id}")
def delete_account(account_id: int, user_id: str):
    conn = get_db_conn()
    execute(conn, f"DELETE FROM accounts WHERE id = {P} AND user_id = {P}", (account_id, user_id))
    conn.close()
    return {"status": "deleted"}


# ─── Payments ─────────────────────────────────────────────────────────────────
def _days(plan_type: str) -> int:
    if "12m" in plan_type: return 365
    if "6m"  in plan_type: return 180
    if "3m"  in plan_type: return 90
    return 30

def _tier(plan_type: str) -> str:
    return "SLOW" if "slow" in plan_type.lower() else "FAST"


@app.post("/api/payment/create")
async def create_payment(data: PaymentRequest):
    plan_labels = {
        "slow_1m":"SLOW 1мес", "slow_3m":"SLOW 3мес", "slow_6m":"SLOW 6мес", "slow_12m":"SLOW 12мес",
        "fast_1m":"FAST 1мес", "fast_3m":"FAST 3мес", "fast_6m":"FAST 6мес", "fast_12m":"FAST 12мес",
    }
    payload_str = f"{data.user_id}|{data.plan_type}|{data.price}"
    body = {
        "asset": "USDT", "amount": str(data.price),
        "currency_type": "fiat", "fiat": "RUB",
        "description": f"FunPay Slow: {plan_labels.get(data.plan_type, data.plan_type)}",
        "payload": payload_str,
        "allow_comments": False, "allow_anonymous": False,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CRYPTO_PAY_URL}/createInvoice", json=body,
            headers={"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN}
        )
    res = resp.json()
    if res.get("ok"):
        return {"payment_url": res["result"]["pay_url"]}
    raise HTTPException(status_code=500, detail=str(res))


@app.post("/api/payment/pay-with-balance")
def pay_with_balance(data: PaymentRequest):
    conn = get_db_conn()
    row = fetchone(conn, f"SELECT balance FROM users WHERE user_id = {P}", (data.user_id,))
    if not row or float(row.get("balance") or 0) < data.price:
        conn.close()
        raise HTTPException(status_code=400, detail="Недостаточно средств на балансе.")
    days    = _days(data.plan_type)
    tier    = _tier(data.plan_type)
    sub_end = int(time.time()) + days * 86400
    execute(conn, f"UPDATE users SET balance=balance-{P}, plan={P}, sub_end={P} WHERE user_id={P}",
            (data.price, tier, sub_end, data.user_id))
    user = fetchone(conn, f"SELECT * FROM users WHERE user_id = {P}", (data.user_id,))
    conn.close()
    return {"status": "success", "user": user_to_api(user)}


@app.post("/api/payment/webhook")
async def crypto_webhook(request: Request):
    data = await request.json()
    if data.get("update_type") != "invoice_paid":
        return {"ok": True}
    payload_str = (data.get("payload") or {}).get("payload", "")
    parts = payload_str.split("|")
    if len(parts) < 3:
        return {"ok": True}
    u_id, p_type, price_str = parts[0], parts[1], parts[2]
    sub_end = int(time.time()) + _days(p_type) * 86400
    conn = get_db_conn()
    execute(conn, f"UPDATE users SET plan={P}, sub_end={P} WHERE user_id={P}", (_tier(p_type), sub_end, u_id))
    ref_row = fetchone(conn, f"SELECT referrer_id FROM users WHERE user_id={P}", (u_id,))
    if ref_row and ref_row.get("referrer_id"):
        execute(conn, f"UPDATE users SET balance=balance+{P} WHERE user_id={P}",
                (float(price_str) * 0.05, ref_row["referrer_id"]))
    conn.close()
    return {"ok": True}


# ─── Admin ────────────────────────────────────────────────────────────────────
@app.get("/api/admin/stats")
def admin_stats(admin_id: str):
    if not is_admin(admin_id):
        raise HTTPException(status_code=403)
    conn = get_db_conn()
    total = fetchone(conn, "SELECT COUNT(*) as c FROM users").get("c", 0)
    fast  = fetchone(conn, f"SELECT COUNT(*) as c FROM users WHERE UPPER(plan)='FAST'").get("c", 0)
    slow  = fetchone(conn, f"SELECT COUNT(*) as c FROM users WHERE UPPER(plan)='SLOW'").get("c", 0)
    conn.close()
    return {"total_users": total, "active_fast": fast, "active_slow": slow, "system_status": "healthy"}


@app.get("/api/admin/users")
def admin_users(admin_id: str):
    if not is_admin(admin_id):
        raise HTTPException(status_code=403)
    conn = get_db_conn()
    rows = fetchall(conn, "SELECT * FROM users ORDER BY created_at DESC")
    conn.close()
    return [user_to_api(r) for r in rows]


@app.post("/api/admin/user/action")
def admin_action(data: AdminUserAction):
    if not is_admin(data.admin_id):
        raise HTTPException(status_code=403)
    conn = get_db_conn()
    if data.action == "ban":
        execute(conn, f"UPDATE users SET is_banned=1 WHERE user_id={P}", (data.target_user_id,))
    elif data.action == "unban":
        execute(conn, f"UPDATE users SET is_banned=0 WHERE user_id={P}", (data.target_user_id,))
    elif data.action == "set_sub":
        sub_end = int(time.time()) + (data.duration_days or 0) * 86400
        plan    = (data.plan or "none").upper()
        execute(conn, f"UPDATE users SET plan={P}, sub_end={P} WHERE user_id={P}", (plan, sub_end, data.target_user_id))
    elif data.action == "update_balance":
        execute(conn, f"UPDATE users SET balance=balance+{P} WHERE user_id={P}", (data.balance_delta, data.target_user_id))
    user = fetchone(conn, f"SELECT * FROM users WHERE user_id={P}", (data.target_user_id,))
    conn.close()
    return {"status": "success", "user": user_to_api(user)}


# ─── Telegram Bot ─────────────────────────────────────────────────────────────
if BOT_TOKEN:
    try:
        import telebot

        bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

        @bot.message_handler(commands=["start"])
        def handle_start(message):
            uid = str(message.from_user.id)
            fname = message.from_user.first_name or "Друг"
            uname = message.from_user.username or ""
            args = message.text.split()
            now = int(time.time())

            # 1. Если это код авторизации (6 цифр)
            if len(args) > 1 and args[1].isdigit() and len(args[1]) == 6:
                code = args[1]
                conn = get_db_conn()
                
                # Ищем токен по коду
                token_row = fetchone(conn, f"SELECT token FROM auth_tokens WHERE code = {P} AND expires > {P}", (code, now))
                
                if token_row:
                    # Создаем или обновляем пользователя
                    user = fetchone(conn, f"SELECT user_id, ref_code FROM users WHERE user_id={P}", (uid,))
                    my_ref = user.get("ref_code") if user else secrets.token_hex(4).upper()
                    
                    if not user:
                        if USE_POSTGRES:
                            execute(conn, f"INSERT INTO users (user_id, first_name, username, plan, ref_code, created_at) VALUES ({P},{P},{P},'none',{P},{P})", (uid, fname, uname, my_ref, now))
                        else:
                            execute(conn, f"INSERT INTO users (user_id, first_name, username, plan, ref_code, created_at) VALUES ({P},{P},{P},'none',{P},{P})", (uid, fname, uname, my_ref, now))
                    
                    # Привязываем user_id к токену сессии
                    execute(conn, f"UPDATE auth_tokens SET user_id = {P} WHERE code = {P}", (uid, code))
                    conn.close()
                    
                    bot.send_message(message.chat.id, 
                        f"✅ <b>Авторизация успешна!</b>\n\n"
                        f"Вход в аккаунт <b>{fname}</b> подтвержден.\n"
                        f"Вернитесь в браузер, система пропустит вас автоматически. 🐌"
                    )
                    return
                else:
                    conn.close()
                    bot.send_message(message.chat.id, "❌ <b>Код недействителен или устарел.</b>\nПопробуйте обновить страницу на сайте.")
                    return

            # 2. Если это реферальная ссылка (ref_XXXX)
            if len(args) > 1 and args[1].startswith("ref_"):
                ref_code_in = args[1][4:]
                conn = get_db_conn()
                referrer = fetchone(conn, f"SELECT user_id FROM users WHERE ref_code={P}", (ref_code_in,))
                my_ref = secrets.token_hex(4).upper()
                if not referrer:
                    bot.send_message(message.chat.id, "❌ Реферальный код не найден.")
                else:
                    if USE_POSTGRES:
                        execute(conn, f"INSERT INTO users (user_id, first_name, username, plan, ref_code, referrer_id, created_at) VALUES ({P},{P},{P},'none',{P},{P},{P}) ON CONFLICT (user_id) DO NOTHING", (uid, fname, uname, my_ref, referrer.get("user_id"), now))
                    else:
                        execute(conn, f"INSERT OR IGNORE INTO users (user_id, first_name, username, plan, ref_code, referrer_id, created_at) VALUES ({P},{P},{P},'none',{P},{P},{P})", (uid, fname, uname, my_ref, referrer.get("user_id"), now))
                    bot.send_message(message.chat.id, f"👋 <b>Привет, {fname}!</b>\n\nВы зарегистрированы по реферальной ссылке. Войдите на сайт через «Войти через Telegram».")
                conn.close()
                return

            # 3. Обычный старт
            conn = get_db_conn()
            user = fetchone(conn, f"SELECT plan, balance FROM users WHERE user_id={P}", (uid,))
            conn.close()
            
            if user:
                bot.send_message(message.chat.id, 
                    f"🐌 <b>Вы в системе, {fname}!</b>\n\n"
                    f"🎫 Тариф: <b>{user.get('plan', 'NONE')}</b>\n"
                    f"💰 Баланс: <b>{user.get('balance', 0)} ₽</b>\n\n"
                    f"Используйте сайт для управления аккаунтами.",
                    reply_markup=telebot.types.InlineKeyboardMarkup().add(
                        telebot.types.InlineKeyboardButton("🌐 Перейти на сайт", url="https://funpay-slow.vercel.app")
                    )
                )
            else:
                bot.send_message(message.chat.id,
                    f"👋 <b>FunPay Slow Bot</b>\n\n"
                    f"Чтобы войти в свой профиль на сайте:\n"
                    f"1. Нажмите кнопку <b>«Войти через Telegram»</b> на сайте.\n"
                    f"2. Бот пришлет вам персональную ссылку.\n\n"
                    f"Ждем вас! 🐌"
                )

        @bot.message_handler(commands=["status"])
        def handle_status(message):
            uid = str(message.from_user.id)
            conn = get_db_conn()
            row = fetchone(conn, f"SELECT * FROM users WHERE user_id={P}", (uid,))
            conn.close()
            if not row:
                bot.send_message(message.chat.id, "❌ Вы не зарегистрированы. Войдите через сайт.")
                return
            u = user_to_api(row)
            days = max(0, (u["sub_end"] - int(time.time())) // 86400) if u["sub_end"] > 0 else 0
            bot.send_message(message.chat.id,
                f"📊 <b>Ваш аккаунт</b>\n\n"
                f"🎫 Тариф: <b>{u['plan']}</b>\n"
                f"⏱ Осталось: <b>{days} дн.</b>\n"
                f"💰 Баланс: <b>{u['balance']} ₽</b>\n"
                f"🔑 Реф-код: <code>{u['ref_code']}</code>"
            )

        def _run_bot():
            print("✅ Telegram bot polling started")
            bot.remove_webhook()
            while True:
                try:
                    bot.infinity_polling(timeout=60, long_polling_timeout=30)
                except Exception as e:
                    print(f"⚠️ Bot error, restarting in 5s: {e}")
                    time.sleep(5)

        threading.Thread(target=_run_bot, daemon=True).start()
        print("✅ Bot thread launched")

    except ImportError:
        print("⚠️ pyTelegramBotAPI not installed — bot disabled")
    except Exception as e:
        print(f"⚠️ Bot init error: {e}")
else:
    print("⚠️ BOT_TOKEN not set — bot disabled")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
