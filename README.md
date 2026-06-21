# 📈 AI-Driven Swing Trading App

An automated, AI-powered stock analysis and swing trading platform focusing on the Indian Equities Market (NSE). This application leverages web scraping, LLM-based sentiment analysis, and real-time market data to identify high-probability 3-5 day trading setups.

## 🌟 Features

- **Automated Morning Analysis**: Background CRON jobs run daily to analyze all active tickers in your watchlist.
- **Smart News Aggregation**: Utilizes Google News RSS feeds to aggregate the latest articles, followed by deep-dive web scraping for full-text context.
- **Advanced LLM Inference**: Powered by Groq's lightning-fast `llama-3.3-70b-versatile` to extract sentiment, identify key drivers, calculate conviction scores, and flag potential risk factors.
- **Capital Protection Failsafes**: Integrates real-time GIFT Nifty checks. If the broader market is too risky (gap down > 1%), all long trades are suspended.
- **Feedback Loop**: Tracks active trades, automatically updating their status as 'Success' (hit +5% target) or 'Failure' (hit -2% stop loss).
- **Modern Dashboard**: A slick React/Vite frontend to manually trigger analyses, manage watchlists, and view prediction scorecards.

---

## 🏗️ Architecture

### Backend (`/backend`)
The backend is built with **Python** and **FastAPI**, designed for speed and asynchronous processing.

1. **API Layer (`main.py`)**: Exposes REST endpoints for the frontend, including manual triggers for analysis and frontend data hydration.
2. **Task Scheduler (`tasks/scheduler.py`)**: Uses `APScheduler` to run `run_morning_analysis` at 8:45 AM IST and `run_feedback_loop` at 9:15 AM IST.
3. **LLM Service (`services/llm_service.py`)**: Interfaces with the Groq API. Constructs structured JSON prompts, pushing scraped news context to the LLM to generate precise trading predictions.
4. **News Scraper (`services/scraper.py`)**: Bypasses anti-bot mechanisms using human-like delays and Referer spoofing to extract main paragraph text via `BeautifulSoup`.
5. **Database Client (`services/supabase_client.py`)**: Maps data models and interacts with **Supabase (PostgreSQL)** for persistent storage of `tickers` and `predictions`.
6. **Market Data (`services/market_data.py`)**: Wraps `yfinance` to fetch live prices, historical data, and broader index health.

### Frontend (`/frontend`)
The frontend is built with **React**, powered by **Vite**, and styled with **TailwindCSS v4**.

- **Dashboard**: Central hub showing the win-rate scorecard and the active watchlist count.
- **Watchlist Manager**: Dynamic search system (falling back intelligently on Yahoo Finance to isolate `.NS` Indian equities) that updates the backend database.
- **Manual Triggers**: Interactive UI elements to trigger the Morning Analysis on-demand.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase Account
- Groq API Key

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install fastapi uvicorn apscheduler yfinance groq beautifulsoup4 feedparser supabase python-dotenv pytz pydantic
   ```
4. Configure your environment variables:
   Create a `.env` file in the `backend` directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_public_key
   TZ="Asia/Kolkata"
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```

---

## 💾 Database Schema (Supabase)

To run this application, you must have the following tables created in your Supabase project:

**`tickers` Table**
- `id` (uuid)
- `symbol` (text) - e.g., "RELIANCE.NS"
- `is_active` (boolean) - default `true`

**`predictions` Table**
- `id` (uuid)
- `ticker` (text)
- `prediction_date` (date)
- `entry_price` (float)
- `target_price` (float)
- `sentiment_score` (float) - Normalized 0.0 to 1.0
- `confidence` (float) - 0.0 to 1.0
- `reasoning` (text) - Contains concatenated Drivers, Risks, and Data Integrity info.
- `status` (text) - default `"pending"` (updates to `"success"` or `"failure"`)
- `raw_sentiment` (float) - _Optional/Recommended: from -1.0 to +1.0_

---

## 🛡️ Best Practices & Notes

- **API Limits**: The backend is hardcoded to respect Groq's free-tier rate limits (5 requests per minute). Do not remove the `time.sleep(12)` in `scheduler.py` unless you upgrade to a paid Groq plan.
- **Scraping Integrity**: If `Moneycontrol` or other news sites block the scraper, the system will seamlessly fallback to using the Google News RSS snippets and automatically mark the trade's data integrity score lower.
- **Timezone**: Ensure the server runs on IST (`Asia/Kolkata`), as all market logic, Nifty triggers, and crons are calibrated for the opening of the Indian markets at 9:15 AM.
