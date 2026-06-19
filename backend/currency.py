import httpx
from typing import Dict

CBU_API_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
TARGET_CURRENCIES = {"USD", "EUR", "RUB", "CNY", "GBP"}

CURRENCY_NAMES = {
    "USD": "AQSH dollari",
    "EUR": "Yevro",
    "RUB": "Rossiya rubli",
    "CNY": "Xitoy yuani",
    "GBP": "Britaniya funt sterlingi",
}


async def get_currency_rates() -> Dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(CBU_API_URL)
            response.raise_for_status()
            data = response.json()

            rates = {}
            for item in data:
                ccy = item.get("Ccy", "")
                if ccy in TARGET_CURRENCIES:
                    rates[ccy] = {
                        "name": CURRENCY_NAMES.get(ccy, item.get("CcyNm_UZ", ccy)),
                        "rate": float(item.get("Rate", 0)),
                        "diff": float(item.get("Diff", 0)),
                        "date": item.get("Date", ""),
                    }

            return rates
    except httpx.TimeoutException:
        return {"error": "Vaqt tugadi, qayta urinib ko'ring"}
    except Exception as e:
        return {"error": f"Kurs ma'lumotlarini olishda xato: {str(e)}"}
