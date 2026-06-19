import asyncio
import os

import google.generativeai as genai

# Initialise once at import time — env vars are stable for the lifetime of a process.
_api_key = os.getenv("GOOGLE_API_KEY", "")
_model = None

if _api_key:
    genai.configure(api_key=_api_key)
    _model = genai.GenerativeModel("gemini-1.5-flash")

_MISSING_KEY_MSG = (
    "Kechirasiz, AI xizmati hozirda faol emas. "
    "Render.com muhit o'zgaruvchilarida GOOGLE_API_KEY ni sozlang."
)


async def get_financial_advice(user_message: str, financial_summary: str = "") -> str:
    if not _model:
        return _MISSING_KEY_MSG

    prompt = f"""Siz "Moliyachi" — O'zbekiston moliyaviy maslahatchi botisiz.
Faqat O'zbek tilida javob bering. Qisqa, amaliy va foydali maslahatlar bering.
Javoblaringiz maksimal 5 gap bo'lsin. Oddiy til ishlating, rasmiy emas.

Foydalanuvchining moliyaviy holati:
{financial_summary if financial_summary else "Ma'lumot yo'q"}

Savol: {user_message}

Javob (O'zbek tilida):"""

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: _model.generate_content(prompt))
        return response.text.strip()
    except Exception as e:
        return f"Kechirasiz, so'rovni bajarishda xato yuz berdi: {str(e)}"
