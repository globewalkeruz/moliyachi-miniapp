import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "moliyachi.db"


async def init_db():
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def add_transaction(user_id: int, amount: float, type: str, category: str, description: str = None):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT INTO transactions (user_id, amount, type, category, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, abs(amount), type, category, description),
        )
        await db.commit()


async def get_transactions(user_id: int, limit: int = 50):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, user_id, amount, type, category, description,
               strftime('%Y-%m-%d %H:%M', created_at) as created_at
               FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute(
            """SELECT COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE -amount END), 0)
               FROM transactions WHERE user_id = ?""",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return float(row[0]) if row else 0.0


async def get_monthly_stats(user_id: int) -> tuple[float, float]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        async with db.execute(
            """SELECT type, COALESCE(SUM(amount), 0) as total
               FROM transactions
               WHERE user_id = ?
               AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')
               GROUP BY type""",
            (user_id,),
        ) as cursor:
            income, expense = 0.0, 0.0
            async for row in cursor:
                if row[0] == "income":
                    income = float(row[1])
                else:
                    expense = float(row[1])
            return income, expense


async def get_monthly_report(user_id: int):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT type, category, COALESCE(SUM(amount), 0) as total
               FROM transactions
               WHERE user_id = ?
               AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')
               GROUP BY type, category
               ORDER BY total DESC""",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def ensure_user(telegram_id: int, first_name: str, last_name: str = None, username: str = None):
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users (telegram_id, first_name, last_name, username)
               VALUES (?, ?, ?, ?)""",
            (telegram_id, first_name, last_name, username),
        )
        await db.commit()
