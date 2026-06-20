import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase() -> Client:
    logging.debug("get_supabase called")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be set in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_active_tickers():
    logging.info("get_active_tickers called")
    supabase = get_supabase()
    response = supabase.table("tickers").select("*").eq("is_active", True).execute()
    return response.data

def get_predictions_for_date(prediction_date: str):
    logging.info(f"get_predictions_for_date called for {prediction_date}")
    supabase = get_supabase()
    response = supabase.table("predictions").select("*").eq("prediction_date", prediction_date).execute()
    return response.data

def save_prediction(data: dict):
    logging.info(f"save_prediction called with data for ticker: {data.get('ticker')}")
    supabase = get_supabase()
    response = supabase.table("predictions").insert(data).execute()
    return response.data

def update_prediction_status(prediction_id: str, status: str):
    logging.info(f"update_prediction_status called for {prediction_id} -> {status}")
    supabase = get_supabase()
    response = supabase.table("predictions").update({"status": status}).eq("id", prediction_id).execute()
    return response.data

def get_pending_predictions():
    logging.info("get_pending_predictions called")
    supabase = get_supabase()
    response = supabase.table("predictions").select("*").eq("status", "pending").execute()
    return response.data

def get_all_predictions():
    logging.info("get_all_predictions called")
    supabase = get_supabase()
    response = supabase.table("predictions").select("*").order("prediction_date", desc=True).execute()
    return response.data

def add_new_ticker(symbol):
    logging.info(f"add_new_ticker called for {symbol}")
    supabase = get_supabase()
    response = supabase.table("tickers").insert({"symbol": symbol.upper()}).execute()
    return response.data

def remove_ticker(symbol):
    logging.info(f"remove_ticker called for {symbol}")
    supabase = get_supabase()
    response = supabase.table("tickers").delete().eq("symbol", symbol.upper()).execute()
    return response.data