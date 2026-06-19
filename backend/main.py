import os
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import database
from currency import get_currency_rates
from gemini_ai import get_financial_advice
from models import AIAdviceRequest, TransactionCreate

load_dotenv()

app = FastAPI(title="Moliyachi — Shaxsiy Moliya Menejeri")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

UZBEK_MONTHS = {
    1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
    5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
    9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr",
}


@app.on_event("startup")
async def startup():
    await database.init_db()
    token = os.getenv("TELEGRAM_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")
    if token and webhook_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{token}/setWebhook",
                    json={"url": f"{webhook_url}/webhook"},
                )
                print(f"Webhook natijasi: {resp.json()}")
        except Exception as e:
            print(f"Webhook xatosi: {e}")


@app.get("/")
async def serve_frontend():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ──────────────────────────────────────────────
# Transactions
# ──────────────────────────────────────────────

@app.post("/api/transaction")
async def add_transaction(data: TransactionCreate):
    try:
        await database.add_transaction(
            user_id=data.user_id,
            amount=data.amount,
            type=data.type,
            category=data.category,
            description=data.description,
        )
        return {"success": True, "message": "Tranzaksiya muvaffaqiyatli qo'shildi"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/transactions/{user_id}")
async def get_transactions(user_id: int, limit: int = 50):
    try:
        txs = await database.get_transactions(user_id, limit)
        return {"transactions": txs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# Balance
# ──────────────────────────────────────────────

@app.get("/api/balance/{user_id}")
async def get_balance(user_id: int):
    try:
        balance = await database.get_balance(user_id)
        income, expense = await database.get_monthly_stats(user_id)
        return {
            "balance": balance,
            "month_income": income,
            "month_expense": expense,
            "user_id": user_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────

@app.get("/api/report/{user_id}")
async def get_report(user_id: int):
    try:
        report_data = await database.get_monthly_report(user_id)
        income_by_cat: dict[str, float] = {}
        expense_by_cat: dict[str, float] = {}
        income_total = 0.0
        expense_total = 0.0

        for r in report_data:
            if r["type"] == "income":
                income_by_cat[r["category"]] = float(r["total"])
                income_total += float(r["total"])
            else:
                expense_by_cat[r["category"]] = float(r["total"])
                expense_total += float(r["total"])

        now = datetime.now()
        return {
            "month": now.strftime("%Y-%m"),
            "month_name": f"{UZBEK_MONTHS[now.month]} {now.year}",
            "income_total": income_total,
            "expense_total": expense_total,
            "net": income_total - expense_total,
            "income_by_category": [{"category": k, "total": v} for k, v in income_by_cat.items()],
            "expense_by_category": [{"category": k, "total": v} for k, v in expense_by_cat.items()],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# Currency
# ──────────────────────────────────────────────

@app.get("/api/currency")
async def get_currency():
    try:
        rates = await get_currency_rates()
        return {"rates": rates, "updated": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# AI Advice
# ──────────────────────────────────────────────

@app.post("/api/ai-advice")
async def ai_advice(data: AIAdviceRequest):
    try:
        balance = await database.get_balance(data.user_id)
        income, expense = await database.get_monthly_stats(data.user_id)
        summary = (
            f"Umumiy balans: {balance:,.0f} so'm\n"
            f"Bu oylik daromad: {income:,.0f} so'm\n"
            f"Bu oylik xarajat: {expense:,.0f} so'm\n"
            f"Tejash: {(income - expense):,.0f} so'm"
        )
        advice = await get_financial_advice(data.message, summary)
        return {"advice": advice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────
# Telegram Webhook
# ──────────────────────────────────────────────

@app.post("/webhook")
async def telegram_webhook(request: Request):
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        return {"ok": False}

    try:
        update = await request.json()
        if "message" not in update:
            return {"ok": True}

        message = update["message"]
        chat_id = message["chat"]["id"]
        user = message.get("from", {})

        await database.ensure_user(
            telegram_id=user.get("id", 0),
            first_name=user.get("first_name", "Foydalanuvchi"),
            last_name=user.get("last_name"),
            username=user.get("username"),
        )

        text = message.get("text", "")
        if text.startswith("/start"):
            app_url = os.getenv("WEBHOOK_URL", "")
            first_name = user.get("first_name", "Do'st")
            await _send_message(
                token=token,
                chat_id=chat_id,
                text=(
                    f"👋 Assalomu alaykum, <b>{first_name}</b>!\n\n"
                    "💰 <b>Moliyachi</b>ga xush kelibsiz — shaxsiy moliya menejeringiz!\n\n"
                    "✅ Daromad va xarajatlarni kuzatish\n"
                    "✅ Oylik hisobotlar va grafiklar\n"
                    "✅ AI moliyaviy maslahat (Gemini)\n"
                    "✅ CBU valyuta kurslari\n\n"
                    "📱 Ilovani ochish uchun quyidagi tugmani bosing:"
                ),
                keyboard={
                    "inline_keyboard": [[
                        {"text": "💰 Moliyachini ochish", "web_app": {"url": app_url}}
                    ]]
                },
            )
    except Exception as e:
        print(f"Webhook xatosi: {e}")

    return {"ok": True}


async def _send_message(token: str, chat_id: int, text: str, keyboard: dict = None):
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = keyboard
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload)


# Mount frontend AFTER all API routes
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
