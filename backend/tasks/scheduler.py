import logging
from datetime import datetime
import pytz
import time
from services.supabase_client import (
    get_active_tickers, 
    save_prediction, 
    get_pending_predictions,
    update_prediction_status
)
from services.market_data import (
    get_current_price, 
    check_gift_nifty_status, 
    check_us_market_status
)
from services.llm_service import analyze_stock_sentiment

IST = pytz.timezone('Asia/Kolkata')

def prepare_data_for_supabase(analysis: dict):
    logging.info("prepare_data_for_supabase called")
    # 1. Map -1.0 to 1.0 range -> 0.0 to 1.0 range
    raw_sentiment = analysis.get("overall_sentiment", 0.0)
    mapped_sentiment = (raw_sentiment + 1) / 2.0
    
    # 2. Combine reasoning into a single string for backward compatibility
    data_tier = "FULL-TEXT" if analysis.get("data_integrity_score", 0.0) > 0.6 else "HEADLINE-ONLY"
    
    drivers = ", ".join(analysis.get("key_drivers", []))
    risks = ", ".join(analysis.get("risk_factors", []))
    
    predicted_move = analysis.get("predicted_move", "NEUTRAL")
    
    combined_reasoning = (
        f"[{data_tier}] Predicted Move: {predicted_move}. "
        f"Drivers: {drivers}. Risks: {risks}."
    )
    
    # Ensure confidence is a float between 0.0 and 1.0 (sometimes LLMs return 0-100)
    confidence = analysis.get("confidence", 0.0)
    if confidence > 1.0:
        confidence = confidence / 100.0
        
    return {
        "sentiment_score": mapped_sentiment,
        "reasoning": combined_reasoning,
        "confidence": confidence,
        # "raw_sentiment": raw_sentiment, # Recommended: Add this column to Supabase!
        "updated_at": datetime.now(pytz.utc).isoformat()
    }

def run_morning_analysis():
    """
    1. Fetches active tickers.
    2. Gets market context.
    3. Calls Gemini for each ticker.
    4. Saves prediction to Supabase.
    """
    logging.info("Starting morning analysis...")
    tickers = get_active_tickers()
    if not tickers:
        logging.warning("No active tickers found.")
        return 0, []

    gift_nifty_change = check_gift_nifty_status()
    us_market_status = check_us_market_status()
    
    if gift_nifty_change < -1.0:
        logging.warning("Market too risky (GIFT Nifty < -1.0%). Skipping all Buy predictions today.")
        return 0, []
    
    today_ist = datetime.now(IST).date().isoformat()
    
    predictions_made = 0
    analyzed_tickers = []
    
    for t in tickers:
        symbol = t.get('symbol')
        analyzed_tickers.append(symbol)
        logging.info(f"Analyzing {symbol}...")
        
        current_price = get_current_price(symbol)
        if current_price <= 0:
            logging.warning(f"Could not fetch price for {symbol}, skipping.")
            continue
            
        try:
            analysis = analyze_stock_sentiment(symbol, gift_nifty_change, us_market_status)
        except Exception as e:
            if "429" in str(e):
                logging.warning(f"Rate limit hit (429) for {symbol}. Waiting 60 seconds before retrying...")
                time.sleep(60)
                try:
                    analysis = analyze_stock_sentiment(symbol, gift_nifty_change, us_market_status)
                except Exception as retry_e:
                    logging.error(f"Retry failed for {symbol}: {retry_e}")
                    time.sleep(12) # Still sleep to maintain throttle
                    continue
            else:
                logging.error(f"Analysis failed for {symbol}: {e}")
                time.sleep(12)
                continue
                
        # Mandatory delay to respect 5 requests/minute API limit
        time.sleep(12)
        
        # Prepare the data mapped correctly for the Supabase DB
        mapped_data = prepare_data_for_supabase(analysis)
            
        # We save all predictions, frontend filters by confidence > 0.75
        # Target price is entry + 5%
        target_price = current_price * 1.05
        
        pred_data = {
            "ticker": symbol,
            "prediction_date": today_ist,
            "entry_price": current_price,
            "target_price": target_price,
            "sentiment_score": mapped_data["sentiment_score"],
            "confidence": mapped_data["confidence"],
            "reasoning": mapped_data["reasoning"],
            "status": "pending"
        }
        
        try:
            save_prediction(pred_data)
            predictions_made += 1
        except Exception as e:
            logging.error(f"Failed to save prediction for {symbol}: {e}")
            
    logging.info(f"Morning analysis complete. {predictions_made} predictions made.")
    return predictions_made, analyzed_tickers

def run_feedback_loop():
    """
    1. Fetches all pending predictions.
    2. Checks if current price >= target price.
    3. If 5 days have passed and target not hit, mark as failure.
    4. If target hit, mark as success.
    """
    logging.info("Starting feedback loop...")
    pending = get_pending_predictions()
    if not pending:
        logging.info("No pending predictions.")
        return 0
        
    updated_count = 0
    today_ist = datetime.now(IST).date()
    
    for p in pending:
        pred_id = p.get('id')
        symbol = p.get('ticker')
        target_price = p.get('target_price')
        pred_date_str = p.get('prediction_date')
        
        pred_date = datetime.strptime(pred_date_str, "%Y-%m-%d").date()
        days_passed = (today_ist - pred_date).days
        
        current_price = get_current_price(symbol)
        
        # 1. Fetch the Stop Loss price from the DB (calculated as entry_price * 0.98 for 2% SL)
        entry_price = p.get('entry_price')
        stop_loss_price = entry_price * 0.98 # 2% Stop Loss
        
        # 2. Check Failure Conditions (Stop Loss or Expiry)
        if current_price <= stop_loss_price or days_passed >= 5:
            update_prediction_status(pred_id, "failure")
            updated_count += 1
            if current_price <= stop_loss_price:
                logging.info(f"Stop Loss hit for {symbol}. Capital protected. Marked failure.")
            else:
                logging.info(f"Prediction {pred_id} for {symbol} expired (5 days). Marked failure.")
            continue
        
        # 3. Check Target (Success Condition)
        if current_price >= target_price:
            update_prediction_status(pred_id, "success")
            updated_count += 1
            logging.info(f"Prediction {pred_id} for {symbol} hit target! Marked success.")
            
    logging.info(f"Feedback loop complete. {updated_count} predictions updated.")
    return updated_count
