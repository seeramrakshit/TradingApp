import React, { useState, useEffect } from 'react';
import { 
  Activity, TrendingUp, TrendingDown, Clock, 
  AlertTriangle, CheckCircle, XCircle, RefreshCw, Zap,
  Plus, Trash2, List
} from 'lucide-react';
import axios from 'axios';
import { format } from 'date-fns';

const API_BASE = 'http://localhost:8000/api';

const Dashboard = () => {
  const [marketStatus, setMarketStatus] = useState(null);
  const [scorecard, setScorecard] = useState(null);
  const [todayPicks, setTodayPicks] = useState([]);
  const [history, setHistory] = useState([]);
  const [tickers, setTickers] = useState([]);
  const [newTicker, setNewTicker] = useState('');
  const [addingTicker, setAddingTicker] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [marketRes, scoreRes, picksRes, histRes, tickersRes] = await Promise.all([
        axios.get(`${API_BASE}/market-status`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/scorecard`).catch(() => ({ data: null })),
        axios.get(`${API_BASE}/predictions/today`).catch(() => ({ data: [] })),
        axios.get(`${API_BASE}/predictions/history`).catch(() => ({ data: [] })),
        axios.get(`${API_BASE}/tickers`).catch(() => ({ data: [] }))
      ]);

      setMarketStatus(marketRes.data);
      setScorecard(scoreRes.data);
      
      // Filter today's picks with confidence > 0.75
      const highConfidence = (picksRes.data || []).filter(p => p.confidence > 0.75);
      setTodayPicks(highConfidence);
      
      setHistory(histRes.data || []);
      setTickers(tickersRes.data || []);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (newTicker.trim().length >= 2) {
        setIsSearching(true);
        try {
          const res = await axios.get(`${API_BASE}/tickers/search?query=${newTicker.trim()}`);
          setSearchResults(res.data || []);
          setShowDropdown(true);
        } catch (err) {
          console.error("Search failed:", err);
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults([]);
        setShowDropdown(false);
      }
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [newTicker]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await axios.post(`${API_BASE}/analyze`);
      await fetchData(); // Refresh data after analysis
    } catch (error) {
      console.error("Analysis failed:", error);
      alert("Failed to analyze markets. Ensure backend and Supabase are running.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFeedbackLoop = async () => {
    try {
      await axios.post(`${API_BASE}/feedback`);
      await fetchData();
    } catch (error) {
      console.error("Feedback update failed:", error);
    }
  };

  const handleAddTicker = async (e) => {
    e.preventDefault();
    if (!newTicker.trim()) return;
    setAddingTicker(true);
    try {
      await axios.post(`${API_BASE}/tickers`, { symbol: newTicker.trim() });
      setNewTicker('');
      await fetchData();
    } catch (err) {
      console.error("Failed to add ticker", err);
    } finally {
      setAddingTicker(false);
    }
  };

  const handleRemoveTicker = async (symbol) => {
    try {
      await axios.delete(`${API_BASE}/tickers/${symbol}`);
      await fetchData();
    } catch (err) {
      console.error("Failed to delete ticker", err);
    }
  };

  if (loading && !scorecard) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-neon-green animate-spin" />
      </div>
    );
  }

  const isRiskHigh = marketStatus?.risk_level === 'High';

  return (
    <div className="space-y-6">
      
      {/* Top Actions & Alerts */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Morning Briefing</h1>
          <p className="text-slate-400 text-sm">{format(new Date(), 'EEEE, MMMM do yyyy')}</p>
        </div>
        
        <div className="flex items-center gap-3 w-full md:w-auto">
          <button 
            onClick={handleFeedbackLoop}
            className="flex-1 md:flex-none px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors flex items-center justify-center gap-2"
          >
            <Activity className="w-4 h-4" />
            <span className="text-sm font-medium">Update Outcomes</span>
          </button>
          <button 
            onClick={handleAnalyze}
            disabled={analyzing}
            className="flex-1 md:flex-none btn-primary flex items-center justify-center gap-2"
          >
            {analyzing ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            <span className="text-sm font-medium">
              {analyzing ? 'Analyzing Markets...' : 'Analyze Markets'}
            </span>
          </button>
        </div>
      </div>

      {isRiskHigh && (
        <div className="glass-panel border-red-900/50 bg-red-950/20 p-4 flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 text-neon-red shrink-0" />
          <div>
            <h3 className="text-neon-red font-semibold">Market Risk: High</h3>
            <p className="text-red-200/70 text-sm mt-1">
              GIFT Nifty is down {marketStatus?.gift_nifty_change_pct?.toFixed(2)}%. 
              No trades are recommended today due to broad market weakness.
            </p>
          </div>
        </div>
      )}

      {/* Scorecard */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="glass-card p-5">
          <p className="text-slate-400 text-sm font-medium">Model Win Rate</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white">
              {scorecard?.win_rate?.toFixed(1) || 0}%
            </span>
          </div>
        </div>
        <div className="glass-card p-5 border-t-2 border-t-blue-500/50">
          <p className="text-slate-400 text-sm font-medium">Active Watchlist</p>
          <div className="mt-2 text-3xl font-bold text-blue-400">{tickers.length}</div>
        </div>
        <div className="glass-card p-5">
          <p className="text-slate-400 text-sm font-medium">Total Predictions</p>
          <div className="mt-2 text-3xl font-bold text-white">{scorecard?.total || 0}</div>
        </div>
        <div className="glass-card p-5 border-t-2 border-t-neon-green/50">
          <p className="text-slate-400 text-sm font-medium">Successes</p>
          <div className="mt-2 text-3xl font-bold text-neon-green">{scorecard?.success || 0}</div>
        </div>
        <div className="glass-card p-5 border-t-2 border-t-neon-red/50">
          <p className="text-slate-400 text-sm font-medium">Failures</p>
          <div className="mt-2 text-3xl font-bold text-neon-red">{scorecard?.failure || 0}</div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        
        {/* Today's Picks */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-neon-green" /> 
            Today's Top Picks
          </h2>
          
          {todayPicks.length === 0 ? (
            <div className="glass-panel p-8 text-center flex flex-col items-center justify-center border-dashed">
              <Activity className="w-10 h-10 text-slate-600 mb-3" />
              <p className="text-slate-400 font-medium">No high-confidence setups found today.</p>
              <p className="text-slate-500 text-sm mt-1">Try running the market analysis.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {todayPicks.map((pick) => (
                <div key={pick.id} className="glass-card p-5 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-neon-green/5 rounded-full blur-3xl -mr-10 -mt-10 transition-transform group-hover:scale-110"></div>
                  
                  <div className="flex justify-between items-start mb-3 relative z-10">
                    <div>
                      <h3 className="text-xl font-bold text-white">{pick.ticker}</h3>
                      <p className="text-sm text-slate-400">Entry: ₹{pick.entry_price?.toFixed(2)}</p>
                    </div>
                    <div className="text-right">
                      <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-neon-green/10 text-neon-green text-xs font-bold border border-neon-green/20">
                        Target: ₹{pick.target_price?.toFixed(2)}
                      </div>
                      <p className="text-xs text-slate-500 mt-1">Conf: {(pick.confidence * 100).toFixed(0)}%</p>
                    </div>
                  </div>
                  
                  <div className="relative z-10 bg-slate-900/50 p-3 rounded border border-slate-700/50">
                    <p className="text-sm text-slate-300 italic leading-relaxed">
                      "{pick.reasoning}"
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: History & Watchlist */}
        <div className="space-y-6">
          
          {/* Historical Log */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-slate-400" /> 
              Recent History
            </h2>
            
            <div className="glass-panel p-1 overflow-hidden">
              <div className="max-h-[300px] overflow-y-auto p-3 space-y-2 custom-scrollbar">
                {history.slice(0, 15).map((item) => (
                  <div key={item.id} className="p-3 rounded bg-slate-800/30 border border-slate-700/30 flex items-center justify-between">
                    <div>
                      <p className="font-bold text-slate-200">{item.ticker}</p>
                      <p className="text-xs text-slate-500">{item.prediction_date}</p>
                    </div>
                    <div>
                      {item.status === 'success' && <CheckCircle className="w-5 h-5 text-neon-green" />}
                      {item.status === 'failure' && <XCircle className="w-5 h-5 text-neon-red" />}
                      {item.status === 'pending' && <Clock className="w-5 h-5 text-slate-400" />}
                    </div>
                  </div>
                ))}
                {history.length === 0 && (
                  <p className="text-center text-slate-500 py-4 text-sm">No historical data.</p>
                )}
              </div>
            </div>
          </div>

          {/* Watchlist Manager */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <List className="w-5 h-5 text-slate-400" /> 
              Watchlist ({tickers.length} stocks)
            </h2>
            <div className="glass-panel p-4">
              <div className="relative mb-4">
                <form onSubmit={handleAddTicker} className="flex gap-2">
                  <div className="relative flex-1">
                    <input 
                      type="text" 
                      value={newTicker}
                      onChange={(e) => setNewTicker(e.target.value)}
                      onFocus={() => { if(searchResults.length > 0) setShowDropdown(true); }}
                      onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
                      placeholder="Search or enter symbol..."
                      className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-neon-green"
                    />
                    {isSearching && (
                      <div className="absolute right-3 top-2.5">
                        <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />
                      </div>
                    )}
                  </div>
                  <button 
                    type="submit" 
                    disabled={addingTicker || !newTicker.trim()}
                    className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-2 rounded border border-slate-700 disabled:opacity-50 transition-colors"
                  >
                    {addingTicker ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  </button>
                </form>

                {/* Dropdown */}
                {showDropdown && searchResults.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-slate-800 border border-slate-700 rounded shadow-xl overflow-hidden max-h-60 overflow-y-auto custom-scrollbar">
                    {searchResults.map((res, idx) => (
                      <div 
                        key={idx} 
                        onClick={() => {
                          setNewTicker(res.symbol);
                          setShowDropdown(false);
                        }}
                        className="p-2 hover:bg-slate-700 cursor-pointer border-b border-slate-700/50 last:border-0 flex justify-between items-center"
                      >
                        <div>
                          <p className="font-bold text-slate-200 text-sm">{res.symbol}</p>
                          <p className="text-xs text-slate-400 truncate max-w-[150px]">{res.name}</p>
                        </div>
                        <span className="text-[10px] uppercase bg-slate-900 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700/50">
                          {res.exch || res.type}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="max-h-[200px] overflow-y-auto space-y-2 custom-scrollbar pr-2">
                {tickers.map(t => (
                  <div key={t.id || t.symbol} className="flex justify-between items-center p-2 rounded bg-slate-800/30 border border-slate-700/30">
                    <span className="font-medium text-slate-200 text-sm">{t.symbol}</span>
                    <button 
                      onClick={() => handleRemoveTicker(t.symbol)}
                      className="text-slate-500 hover:text-neon-red transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {tickers.length === 0 && (
                  <p className="text-center text-slate-500 text-sm py-2">No tickers in watchlist.</p>
                )}
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};

export default Dashboard;
