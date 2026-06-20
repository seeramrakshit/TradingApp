-- Supabase Schema for Swing Trading App

CREATE TABLE tickers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker VARCHAR(20) REFERENCES tickers(symbol) ON DELETE CASCADE,
    prediction_date DATE NOT NULL,
    entry_price DECIMAL(10, 2) NOT NULL,
    target_price DECIMAL(10, 2) NOT NULL,
    sentiment_score DECIMAL(3, 2) NOT NULL,
    confidence DECIMAL(3, 2) NOT NULL,
    reasoning TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- pending, success, failure
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Indexes for performance
CREATE INDEX idx_predictions_ticker ON predictions(ticker);
CREATE INDEX idx_predictions_status ON predictions(status);
CREATE INDEX idx_predictions_date ON predictions(prediction_date);

-- Insert some default active tickers (Nifty 50 subset)
INSERT INTO tickers (symbol, company_name) VALUES
('RELIANCE.NS', 'Reliance Industries Limited'),
('TCS.NS', 'Tata Consultancy Services Limited'),
('HDFCBANK.NS', 'HDFC Bank Limited'),
('INFY.NS', 'Infosys Limited'),
('ICICIBANK.NS', 'ICICI Bank Limited'),
('SBIN.NS', 'State Bank of India'),
('BHARTIARTL.NS', 'Bharti Airtel Limited'),
('ITC.NS', 'ITC Limited'),
('HINDUNILVR.NS', 'Hindustan Unilever Limited'),
('L&T.NS', 'Larsen & Toubro Limited')
ON CONFLICT (symbol) DO NOTHING;
