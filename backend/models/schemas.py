from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

class TickerResponse(BaseModel):
    id: str
    symbol: str
    company_name: Optional[str]
    is_active: bool

class PredictionResponse(BaseModel):
    id: str
    ticker: str
    prediction_date: date
    entry_price: float
    target_price: float
    sentiment_score: float
    confidence: float
    reasoning: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

class AnalyzeResponse(BaseModel):
    status: str
    predictions_made: int
    tickers_analyzed: List[str]

class FeedbackResponse(BaseModel):
    status: str
    updated_predictions: int
