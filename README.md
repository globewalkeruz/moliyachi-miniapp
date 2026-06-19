# Moliyachi — Shaxsiy Moliya Menejeri

Telegram Mini App for personal finance management in Uzbek language.

## Tech Stack

- **Backend**: Python FastAPI + SQLite (aiosqlite)
- **Frontend**: HTML + CSS + Vanilla JS (SPA)
- **AI**: Google Gemini 1.5 Flash
- **Currency**: CBU UZ live rates
- **Deployment**: Render.com

## Local Development

```bash
# 1. Clone and enter the project
cd moliyachiai/mini-app

# 2. Activate virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows Bash
# or: venv\Scripts\activate.bat  (CMD)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your TELEGRAM_TOKEN and GOOGLE_API_KEY

# 5. Run the server
cd backend
uvicorn main:app --reload --port 8000
```

App will be at `http://localhost:8000`

## Deployment on Render.com

1. Push code to GitHub
2. Create a new **Web Service** on Render.com
3. Connect your GitHub repository
4. Render auto-detects `render.yaml` — set your env vars in the dashboard:
   - `TELEGRAM_TOKEN` — from [@BotFather](https://t.me/BotFather)
   - `GOOGLE_API_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey)
   - `WEBHOOK_URL` — your Render app URL (e.g. `https://moliyachi.onrender.com`)
5. Deploy

### Setting GOOGLE_API_KEY on Render.com

1. Open your service in the [Render dashboard](https://dashboard.render.com)
2. Go to **Environment** → **Environment Variables**
3. Click **Add Environment Variable**
4. Set **Key** = `GOOGLE_API_KEY` and **Value** = your key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
5. Click **Save Changes** — Render redeploys automatically

> The AI advisor will show a friendly Uzbek error message if the key is missing or invalid.

## Telegram Bot Setup

1. Open [@BotFather](https://t.me/BotFather) → `/newbot`
2. Set bot name and username
3. Copy the token to `TELEGRAM_TOKEN`
4. After deploying, set the Mini App URL:
   ```
   /newapp → select your bot → set URL to your Render URL
   ```
5. The webhook is registered automatically on startup

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/transaction` | Add income/expense |
| GET | `/api/transactions/{user_id}` | Get all transactions |
| GET | `/api/balance/{user_id}` | Current balance + monthly stats |
| GET | `/api/report/{user_id}` | Monthly report by category |
| GET | `/api/currency` | Live CBU UZ exchange rates |
| POST | `/api/ai-advice` | Gemini AI financial advice |
| POST | `/webhook` | Telegram bot webhook |

## Project Structure

```
mini-app/
├── backend/
│   ├── main.py        # FastAPI app, all routes
│   ├── database.py    # SQLite via aiosqlite
│   ├── gemini_ai.py   # Gemini 1.5 Flash integration
│   ├── currency.py    # CBU UZ exchange rates
│   └── models.py      # Pydantic request models
├── frontend/
│   ├── index.html     # Single-page app shell
│   ├── style.css      # Design system + Telegram theme
│   └── app.js         # All frontend logic
├── requirements.txt
├── .env.example
├── render.yaml
└── moliyachi.db       # Created automatically on first run
```
