import asyncio
import os
from functools import lru_cache

import google.generativeai as genai


@lru_cache(maxsize=1)
def _get_model():
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


async def get_financial_advice(user_message: str, financial_summary: str = "") -> str:
    model = _get_model()
    if not model:
        return "Kechirasiz, AI xizmati hozirda mavjud emas. GEMINI_API_KEY sozlanmagan."

    prompt = f"""Siz "Moliyachi" — O'zbekiston moliyaviy maslahatchi botisiz.
Faqat O'zbek tilida javob bering. Qisqa, amaliy va foydali maslahatlar bering.
Javoblaringiz maksimal 5 gap bo'lsin. Oddiy til ishlating, rasmiy emas.

Foydalanuvchining moliyaviy holati:
{financial_summary if financial_summary else "Ma'lumot yo'q"}

Savol: {user_message}

Javob (O'zbek tilida):"""

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        return response.text.strip()
    except Exception as e:
        return f"Kechirasiz, xato yuz berdi: {str(e)}"
