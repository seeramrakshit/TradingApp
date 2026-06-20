from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from models.schemas import AnalyzeResponse, FeedbackResponse
from services.supabase_client import (
    # get_today_predictions,
    get_all_predictions,
    get_active_tickers,
    add_new_ticker,
    remove_ticker
)
from services.market_data import check_gift_nifty_status
from tasks.scheduler import run_morning_analysis, run_feedback_loop

import yfinance as yf

app = FastAPI(title="Swing Trading API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IST = pytz.timezone('Asia/Kolkata')
scheduler = BackgroundScheduler(timezone=IST)

@app.on_event("startup")
def start_scheduler():
    logging.info("start_scheduler called")
    scheduler.add_job(run_morning_analysis, 'cron', hour=8, minute=45)
    scheduler.add_job(run_feedback_loop, 'cron', hour=9, minute=15)
    scheduler.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    logging.info("shutdown_scheduler called")
    scheduler.shutdown()

@app.get("/")
def health_check():
    logging.info("health_check endpoint called")
    return {"status": "ok", "time_ist": datetime.now(IST).isoformat()}

@app.post("/api/analyze", response_model=AnalyzeResponse)
def trigger_analysis(background_tasks: BackgroundTasks):
    """Manual trigger for morning analysis"""
    logging.info("trigger_analysis endpoint called")
    # Run synchronously for immediate feedback, or return status
    try:
        predictions_made, analyzed_tickers = run_morning_analysis()
        return AnalyzeResponse(
            status="success",
            predictions_made=predictions_made,
            tickers_analyzed=analyzed_tickers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback", response_model=FeedbackResponse)
def trigger_feedback():
    """Manual trigger for feedback loop"""
    logging.info("trigger_feedback endpoint called")
    try:
        updated = run_feedback_loop()
        return FeedbackResponse(status="success", updated_predictions=updated)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predictions/today")
def get_today_picks():
    logging.info("get_today_picks endpoint called")
    today_ist = datetime.now(IST).date().isoformat()
    # Mocking get_predictions_for_date usage or get_today
    # Actually need to implement get_predictions_for_date correctly
    from services.supabase_client import get_predictions_for_date
    preds = get_predictions_for_date(today_ist)
    return preds

@app.get("/api/predictions/history")
def get_history():
    logging.info("get_history endpoint called")
    return get_all_predictions()

@app.get("/api/market-status")
def get_market_status():
    logging.info("get_market_status endpoint called")
    gift_change = check_gift_nifty_status()
    risk_level = "High" if gift_change < -1.0 else "Normal"
    return {
        "gift_nifty_change_pct": gift_change,
        "risk_level": risk_level,
        "warning": "Market Risk: High - No Trades Today" if risk_level == "High" else None
    }

@app.get("/api/scorecard")
def get_scorecard():
    logging.info("get_scorecard endpoint called")
    all_preds = get_all_predictions()
    if not all_preds:
        return {"win_rate": 0, "total": 0, "success": 0, "failure": 0, "pending": 0}
    
    total = len(all_preds)
    success = sum(1 for p in all_preds if p.get('status') == 'success')
    failure = sum(1 for p in all_preds if p.get('status') == 'failure')
    pending = sum(1 for p in all_preds if p.get('status') == 'pending')
    
    resolved = success + failure
    win_rate = (success / resolved * 100) if resolved > 0 else 0.0
    
    return {
        "win_rate": win_rate,
        "total": total,
        "success": success,
        "failure": failure,
        "pending": pending
    }

@app.get("/api/tickers")
def get_tickers():
    logging.info("get_tickers endpoint called")
    return get_active_tickers()

@app.post("/api/tickers")
def add_ticker(ticker: dict):
    logging.info(f"add_ticker endpoint called for {ticker.get('symbol')}")
    # Expects {"symbol": "ZOMATO.NS"}
    # from backend.services.supabase_client import add_new_ticker
    return add_new_ticker(ticker['symbol'])

@app.delete("/api/tickers/{symbol}")
def delete_ticker(symbol: str):
    logging.info(f"delete_ticker endpoint called for {symbol}")
    # from backend.services.supabase_client import remove_ticker
    return remove_ticker(symbol)


@app.get("/api/tickers/search")
def search_tickers(query: str):
    logging.info(f"search_tickers endpoint called with query: {query}")
    try:
        query = query.strip().upper()
        # Increase results to ensure we catch the correct ticker (e.g., NALCO -> NATIONALUM)
        search = yf.Search(query, max_results=15)
        results = []
        
        for quote in search.quotes:
            symbol = quote.get("symbol", "")
            exch = quote.get("exchDisp", "")
            qtype = quote.get("typeDisp", "")
            name = quote.get("shortname", quote.get("longname", "Unknown Company"))

            # 1. Check if it has an Indian suffix (The most reliable check)
            is_nse = symbol.endswith(".NS")
            is_bse = symbol.endswith(".BO")
            
            # 2. Check for Indian Exchange keywords as a fallback
            indian_exch_keywords = ["nse", "bse", "nsi", "bom", "india", "national stock", "bombay"]
            is_indian_exch = any(key in exch.lower() for key in indian_exch_keywords)
            
            # Filter: We want Equities that are clearly Indian
            if qtype.lower() in ["equity", "common stock"] and (is_nse or is_bse or is_indian_exch):
                results.append({
                    "symbol": symbol,
                    "name": name,
                    "exch": "NSE" if is_nse else ("BSE" if is_bse else exch),
                    "type": qtype
                })
        
        # SMART FALLBACK: 
        # If the list is empty, try searching for the word + " NSE"
        if not results:
            forced_search = yf.Search(f"{query} NSE", max_results=5)
            for quote in forced_search.quotes:
                symbol = quote.get("symbol", "")
                if symbol.endswith(".NS"):
                    results.append({
                        "symbol": symbol,
                        "name": quote.get("shortname", "Unknown"),
                        "exch": "NSE",
                        "type": "equity"
                    })
            
        # Sort: Keep NSE (.NS) stocks at the very top for better UX
        results.sort(key=lambda x: x['symbol'].endswith('.NS'), reverse=True)
        
        # Deduplicate
        seen = set()
        unique_results = []
        for r in results:
            if r['symbol'] not in seen:
                unique_results.append(r)
                seen.add(r['symbol'])
                
        return unique_results
    except Exception as e:
        logging.error(f"Search Error for query '{query}': {e}")
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")