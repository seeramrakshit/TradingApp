import yfinance as yf
import logging

def get_current_price(ticker_symbol: str) -> float:
    logging.info(f"get_current_price called for ticker: {ticker_symbol}")
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Fast info usually has the current price
        fast_info = ticker.fast_info
        if 'last_price' in fast_info:
            return float(fast_info['last_price'])
        
        # Fallback to history
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        return 0.0
    except Exception as e:
        logging.error(f"Error fetching price for {ticker_symbol}: {e}")
        return 0.0

def get_historical_price(ticker_symbol: str, days_ago: int) -> float:
    logging.info(f"get_historical_price called for ticker: {ticker_symbol}, days_ago: {days_ago}")
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Fetch a short period to ensure we get a trading day around `days_ago`
        period = f"{days_ago + 5}d"
        hist = ticker.history(period=period)
        if len(hist) > days_ago:
            # -1 is latest, -2 is 1 day ago, etc.
            idx = -(days_ago + 1)
            return float(hist['Close'].iloc[idx])
        elif not hist.empty:
            return float(hist['Close'].iloc[0])
        return 0.0
    except Exception as e:
        logging.error(f"Error fetching historical price for {ticker_symbol}: {e}")
        return 0.0

def check_gift_nifty_status() -> float:
    """
    Returns the percentage change of GIFT Nifty.
    Since GIFT Nifty might not have a direct reliable free yfinance ticker that is always up-to-date,
    we can use a proxy like Nifty 50 futures or SGX Nifty if available, 
    or we return 0.0 if unable to fetch.
    For this implementation, let's try ^NSEI (Nifty 50 index) as a proxy or Nifty futures.
    We will just return a placeholder or calculate 1-day change of ^NSEI.
    """
    logging.info("check_gift_nifty_status called")
    try:
        ticker = yf.Ticker("^NSEI")
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            current = hist['Close'].iloc[-1]
            pct_change = ((current - prev_close) / prev_close) * 100
            return pct_change
        return 0.0
    except Exception as e:
        logging.error(f"Error checking Nifty status: {e}")
        return 0.0

def check_us_market_status() -> str:
    """
    Returns a brief description of US Market (S&P 500) status.
    """
    logging.info("check_us_market_status called")
    try:
        ticker = yf.Ticker("^GSPC")
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            current = hist['Close'].iloc[-1]
            pct_change = ((current - prev_close) / prev_close) * 100
            if pct_change > 0.5:
                return "Bullish"
            elif pct_change < -0.5:
                return "Bearish"
            else:
                return "Neutral"
        return "Neutral"
    except Exception as e:
        logging.error(f"Error checking US market status: {e}")
        return "Neutral"
