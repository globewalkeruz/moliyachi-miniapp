import os
import asyncio
from datetime import datetime
from collections import defaultdict

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        _client = create_client(url, key)
    return _client


async def init_db():
    # Tables are pre-created in Supabase SQL Editor — nothing to do at startup.
    pass


# ──────────────────────────────────────────────
# Transactions
# ──────────────────────────────────────────────

async def add_transaction(user_id: int, amount: float, type: str, category: str, description: str = None):
    def _insert():
        return _get_client().table("transactions").insert({
            "user_id": user_id,
            "amount": abs(amount),
            "type": type,
            "category": category,
            "note": description,
        }).execute()
    await asyncio.to_thread(_insert)


async def get_transactions(user_id: int, limit: int = 50):
    def _query():
        return _get_client().table("transactions") \
            .select("id, user_id, amount, type, category, note, created_at") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
    result = await asyncio.to_thread(_query)
    rows = []
    for r in result.data:
        created = r.get("created_at", "")
        if created:
            created = created[:16].replace("T", " ")
        rows.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "amount": float(r["amount"]),
            "type": r["type"],
            "category": r["category"],
            "description": r.get("note"),
            "created_at": created,
        })
    return rows


async def get_total_stats(user_id: int) -> tuple[float, float]:
    """Return (total_income, total_expense) across all time."""
    def _query():
        return _get_client().table("transactions") \
            .select("amount, type") \
            .eq("user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_query)
    income = sum(float(t["amount"]) for t in result.data if t["type"] == "income")
    expense = sum(float(t["amount"]) for t in result.data if t["type"] == "expense")
    return income, expense


async def get_monthly_report(user_id: int):
    now = datetime.now()
    month_start = f"{now.year}-{now.month:02d}-01"
    if now.month == 12:
        month_end = f"{now.year + 1}-01-01"
    else:
        month_end = f"{now.year}-{now.month + 1:02d}-01"

    def _query():
        return _get_client().table("transactions") \
            .select("type, category, amount") \
            .eq("user_id", user_id) \
            .gte("created_at", month_start) \
            .lt("created_at", month_end) \
            .execute()
    result = await asyncio.to_thread(_query)

    totals: dict[tuple, float] = defaultdict(float)
    for t in result.data:
        totals[(t["type"], t["category"])] += float(t["amount"])

    return [
        {"type": k[0], "category": k[1], "total": v}
        for k, v in sorted(totals.items(), key=lambda x: -x[1])
    ]


async def clear_user_transactions(user_id: int) -> int:
    def _delete():
        return _get_client().table("transactions") \
            .delete() \
            .eq("user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_delete)
    return len(result.data)


async def delete_transaction(transaction_id: str, user_id: int) -> bool:
    def _delete():
        return _get_client().table("transactions") \
            .delete() \
            .eq("id", transaction_id) \
            .eq("user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_delete)
    return len(result.data) > 0


async def ensure_user(telegram_id: int, first_name: str, last_name: str = None, username: str = None):
    name = " ".join(filter(None, [first_name, last_name])) if last_name else first_name

    def _upsert():
        return _get_client().table("users").upsert(
            {"telegram_id": telegram_id, "name": name},
            on_conflict="telegram_id",
        ).execute()
    await asyncio.to_thread(_upsert)


# ──────────────────────────────────────────────
# Categories
# ──────────────────────────────────────────────

async def get_categories(user_id: int) -> list:
    def _query():
        return _get_client().table("categories") \
            .select("*") \
            .eq("telegram_user_id", user_id) \
            .order("created_at") \
            .execute()
    result = await asyncio.to_thread(_query)
    return result.data


async def add_category(user_id: int, name: str, emoji: str, type: str, color: str = None) -> dict | None:
    def _insert():
        return _get_client().table("categories").insert({
            "telegram_user_id": user_id,
            "name": name,
            "emoji": emoji,
            "type": type,
            "color": color,
        }).execute()
    result = await asyncio.to_thread(_insert)
    return result.data[0] if result.data else None


async def delete_category(category_id: str, user_id: int) -> bool:
    def _delete():
        return _get_client().table("categories") \
            .delete() \
            .eq("id", category_id) \
            .eq("telegram_user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_delete)
    return len(result.data) > 0


# ──────────────────────────────────────────────
# Budgets
# ──────────────────────────────────────────────

async def get_budgets(user_id: int) -> list:
    def _query():
        return _get_client().table("budgets") \
            .select("*") \
            .eq("telegram_user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_query)
    return result.data


async def upsert_budget(user_id: int, month: int, year: int, category: str, limit_amount: float) -> dict | None:
    def _upsert():
        return _get_client().table("budgets").upsert({
            "telegram_user_id": user_id,
            "month": month,
            "year": year,
            "category": category,
            "limit_amount": limit_amount,
        }, on_conflict="telegram_user_id,month,year,category").execute()
    result = await asyncio.to_thread(_upsert)
    return result.data[0] if result.data else None


async def delete_budget(user_id: int, month: int, year: int, category: str) -> bool:
    def _delete():
        return _get_client().table("budgets") \
            .delete() \
            .eq("telegram_user_id", user_id) \
            .eq("month", month) \
            .eq("year", year) \
            .eq("category", category) \
            .execute()
    result = await asyncio.to_thread(_delete)
    return len(result.data) > 0


# ──────────────────────────────────────────────
# Scheduled Payments
# ──────────────────────────────────────────────

async def get_scheduled_payments(user_id: int) -> list:
    def _query():
        return _get_client().table("scheduled_payments") \
            .select("*") \
            .eq("telegram_user_id", user_id) \
            .order("created_at") \
            .execute()
    result = await asyncio.to_thread(_query)
    return result.data


async def add_scheduled_payment(
    user_id: int, name: str, amount: float, category: str,
    is_recurring: bool, due_day: int = None, due_date: str = None,
    recurrence_type: str = 'monthly'
) -> dict | None:
    def _insert():
        return _get_client().table("scheduled_payments").insert({
            "telegram_user_id": user_id,
            "name": name,
            "amount": amount,
            "category": category,
            "is_recurring": is_recurring,
            "recurrence_type": recurrence_type,
            "due_day": due_day,
            "due_date": due_date,
            "paid_months": [],
        }).execute()
    result = await asyncio.to_thread(_insert)
    return result.data[0] if result.data else None


async def delete_scheduled_payment(payment_id: str, user_id: int) -> bool:
    def _delete():
        return _get_client().table("scheduled_payments") \
            .delete() \
            .eq("id", payment_id) \
            .eq("telegram_user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_delete)
    return len(result.data) > 0


# ──────────────────────────────────────────────
# Monthly Plans (Next Month Planner)
# ──────────────────────────────────────────────

async def get_monthly_plans(user_id: int, month: int, year: int) -> list:
    def _query():
        return _get_client().table("monthly_plans") \
            .select("*") \
            .eq("telegram_user_id", user_id) \
            .eq("month", month) \
            .eq("year", year) \
            .order("expected_day", nullsfirst=False) \
            .execute()
    result = await asyncio.to_thread(_query)
    return result.data


async def add_monthly_plan(
    user_id: int, month: int, year: int, plan_type: str,
    name: str, amount: float, category: str = '',
    expected_day: int = None, note: str = None
) -> dict | None:
    def _insert():
        return _get_client().table("monthly_plans").insert({
            "telegram_user_id": user_id,
            "month": month,
            "year": year,
            "plan_type": plan_type,
            "name": name,
            "amount": amount,
            "category": category,
            "expected_day": expected_day,
            "note": note,
        }).execute()
    result = await asyncio.to_thread(_insert)
    return result.data[0] if result.data else None


async def delete_monthly_plan(plan_id: str, user_id: int) -> bool:
    def _delete():
        return _get_client().table("monthly_plans") \
            .delete() \
            .eq("id", plan_id) \
            .eq("telegram_user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_delete)
    return len(result.data) > 0


async def mark_scheduled_payment_paid(payment_id: str, user_id: int, month_key: str) -> bool:
    def _get():
        return _get_client().table("scheduled_payments") \
            .select("paid_months") \
            .eq("id", payment_id) \
            .eq("telegram_user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_get)
    if not result.data:
        return False

    paid_months = result.data[0].get("paid_months") or []
    if month_key not in paid_months:
        paid_months = [*paid_months, month_key]

    def _update():
        return _get_client().table("scheduled_payments") \
            .update({"paid_months": paid_months}) \
            .eq("id", payment_id) \
            .eq("telegram_user_id", user_id) \
            .execute()
    result = await asyncio.to_thread(_update)
    return len(result.data) > 0
