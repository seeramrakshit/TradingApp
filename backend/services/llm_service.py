import os
import json
import logging
from datetime import datetime
import yfinance as yf
from groq import Groq
from pydantic import BaseModel
from dotenv import load_dotenv
from services.scraper import scrape_news_content
import feedparser
import urllib.parse

load_dotenv()

# We use a fast, capable model like Llama-3.3-70b-versatile
GROQ_MODEL = 'llama-3.3-70b-versatile'

class SentimentAnalysis(BaseModel):
    ticker: str
    overall_sentiment: float
    data_integrity_score: float
    predicted_move: str
    confidence: float
    impact_weight: float
    key_drivers: list[str]
    risk_factors: list[str]
    data_warning: str

def fetch_google_news_rss(ticker):
    """
    Fetches news from Google News RSS for a specific Indian stock ticker.
    """
    logging.info(f"fetch_google_news_rss called for {ticker}")
    # For Indian stocks, we search for the Ticker + 'stock news'
    search_query = f"{ticker} stock news"
    encoded_query = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    feed = feedparser.parse(rss_url)
    news_items = []
    
    # Take top 5 recent items
    for entry in feed.entries[:5]:
        news_items.append({
            'title': entry.title,
            'link': entry.link,
            'publisher': entry.source.get('title', 'Unknown') if hasattr(entry, 'source') else 'Unknown',
            'published': entry.published if hasattr(entry, 'published') else 'Unknown time',
            'summary': entry.summary if hasattr(entry, 'summary') else 'No summary available'
        })
    return news_items

def analyze_stock_sentiment(ticker: str, gift_nifty_change: float, us_market_status: str) -> dict:
    logging.info(f"analyze_stock_sentiment called for ticker: {ticker}")
    # Handle the specific GORQ typo from .env or standard GROQ
    api_key = os.getenv("GORQ_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": "API Key Missing"}
    
    client = Groq(api_key=api_key)
    
    # --- STEP 1: FETCH & SCRAPE NEWS ---
    try:
        logging.info(f"Fetching RSS news for {ticker}...")
        news_items = fetch_google_news_rss(ticker)
        news_context = ""
        
        if news_items:
            for i, item in enumerate(news_items):
                news_context += f"--- Article {i+1} ---\n"
                news_context += f"Title: [{item['publisher']}] {item['title']}\n"
                news_context += f"Timestamp: {item['published']}\n"
                
                # Scrape full article text using your existing scraper
                logging.info(f"Scraping link: {item['link']}")
                full_text = scrape_news_content(item['link'])
                
                if full_text:
                    news_context += f"Content: {full_text}\n\n"
                else:
                    # FALLBACK: Use RSS Summary/Snippet
                    news_context += f"Content: [Full text blocked. RSS Summary: {item['summary']}]\n\n"
        else:
            news_context = "No recent news found on Google News."
    except Exception as e:
        logging.warning(f"RSS Fetch failed for {ticker}: {e}")
        news_context = "Could not fetch news."

    # --- STEP 2: GROQ INFERENCE ---
    try:
        prompt = f"""
        You are a Senior Quantitative Financial Analyst. You will be provided with {len(news_items) if 'news_items' in locals() and news_items else 0} scraped news articles for {ticker}, sorted from newest to oldest.

        TICKER: {ticker}
        
        Recent News Context:
        {news_context}
        
        Current Market Context:
        - GIFT Nifty: {gift_nifty_change}%
        - US Markets: {us_market_status}
        
        Your Goal:
        - Sentiment Scoring: Rate the overall sentiment for this stock from -1.0 (Strongly Bearish) to 1.0 (Strongly Bullish).
        - Impact Assessment: Assign an "Impact Weight" (0.0 to 1.0) to indicate how likely this news is to move the stock price.
        - Future Prediction: Based strictly on the provided text, predict the likely price direction (UP, DOWN, or NEUTRAL) for the next 24-48 hours.
        - Confidence Level: Provide a float (0.0 to 1.0) indicating your confidence in this analysis.
        
        Rules:
        - Identify if the news is "Fresh" or "Stale" based on the timestamps.
        - Focus on high-signal drivers like earnings, regulatory changes, or product launches.
        - Important: Some items may only contain a "Headline" if the full text was unavailable.
        - Assign a Data Integrity Score (0.0 to 1.0). If you only have headlines, this score should be below 0.5.
        - If data integrity is low, provide a "NEUTRAL" prediction unless the headline is extremely significant (e.g., "CEO Resigns").
        
        Return ONLY a JSON object. No conversational filler.
        
        Output Schema:
        {{
            "ticker": "{ticker}",
            "overall_sentiment": float,
            "data_integrity_score": float,
            "predicted_move": "string (UP/DOWN/NEUTRAL)",
            "confidence": float,
            "impact_weight": float,
            "key_drivers": ["Driver 1", "Driver 2"],
            "risk_factors": ["Factor 1"],
            "data_warning": "string (e.g., 'Analysis based on headlines only')"
        }}
        """

        logging.info(f"Analyzing {ticker} with Groq ({GROQ_MODEL})...")
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You output JSON and only JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        if "429" in str(e):
            raise e
        logging.error(f"Groq API Error for {ticker}: {e}")
        return {
            "ticker": ticker,
            "overall_sentiment": 0.0,
            "data_integrity_score": 0.0,
            "predicted_move": "NEUTRAL",
            "confidence": 0.0,
            "impact_weight": 0.0,
            "key_drivers": [],
            "risk_factors": [],
            "data_warning": f"Formatting Error or API Error: {e}"
        }
