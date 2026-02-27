"""
data_manager.py - Intelligent Data Management with Caching
Upgraded from swing_system with cache optimization

Features:
  - Alpha Vantage integration (no external deps)
  - CSV cache (avoid repeated API calls)
  - Synthetic data generation
  - Rate limiting
  - S&P 500 subset integration
"""

import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import numpy as np
import pandas as pd


# ==================== CONFIGURATION ====================

CACHE_DIR = Path("tradingagents/data/cache")
MANUAL_DIR = Path("tradingagents/data/manual")
CONFIG_FILE = Path("config_fase3.json")

OHLCV_COLS = ["open", "high", "low", "close", "volume"]

# S&P 500 subset by sector
SP500_SUBSET = {
    "technology": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "CRM", "ADBE"],
    "financials": ["JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP", "BLK", "SCHW"],
    "healthcare": ["UNH", "JNJ", "PFE", "ABBV", "MRK", "TMO", "ABT", "LLY", "MCD", "CI"],
    "industrials": ["CAT", "BA", "GE", "HON", "UPS", "LMT", "RTX", "MMM", "DE", "EW"],
    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PSX", "MPC", "VLO", "HAL", "OXY"],
    "indices": ["SPY", "QQQ", "IWM", "DIA"],
}


def load_config() -> dict:
    """Carica configurazione o usa defaults."""
    defaults = {
        "api_key": "demo",
        "cache_days": 1,
        "rate_limit_sleep": 12,
        "min_history_days": 252,
        "full_output_threshold": 30,
        "watchlist": None,
    }
    
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            user_cfg = json.load(f)
        defaults.update(user_cfg)
    
    return defaults


# ==================== ALPHA VANTAGE CLIENT ====================

class AlphaVantageClient:
    """Minimale Alpha Vantage client (zero external deps)."""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self, api_key: str, sleep_between_calls: float = 12.0):
        self.api_key = api_key
        self.sleep_secs = sleep_between_calls
        self._call_count = 0
        self._last_call = 0
    
    def _get(self, params: dict) -> dict:
        """Esegue GET request."""
        params["apikey"] = self.api_key
        url = self.BASE_URL + "?" + urllib.parse.urlencode(params)
        
        # Rate limiting
        elapsed = time.time() - self._last_call
        if elapsed < self.sleep_secs:
            time.sleep(self.sleep_secs - elapsed)
        
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            raise ConnectionError(f"Alpha Vantage error: {e}")
        
        if "Note" in data:
            raise RuntimeError(f"Rate limited: {data['Note']}")
        if "Error Message" in data:
            raise ValueError(f"API error: {data['Error Message']}")
        
        self._call_count += 1
        self._last_call = time.time()
        return data
    
    def daily_adjusted(self, symbol: str, outputsize: str = "full") -> Dict:
        """Scarica dati daily adjusted."""
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": outputsize,
        }
        return self._get(params)


# ==================== DATA MANAGER ====================

class DataManager:
    """Gestisce download, cache, e dati per il backtesting."""
    
    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = AlphaVantageClient(
            self.config.get("api_key", "demo"),
            self.config.get("rate_limit_sleep", 12.0)
        )
    
    def get(self, symbol: str, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """
        Scarica dati per un simbolo.
        
        Strategia:
          1. Se cache disponibile e recente, ritorna celui
          2. Altrimenti, scarica da API
        """
        cache_path = self.cache_dir / f"{symbol}.csv"
        
        # Try cache
        if use_cache and cache_path.exists():
            cache_age_days = (datetime.now() - datetime.fromtimestamp(
                cache_path.stat().st_mtime
            )).days
            
            if cache_age_days <= self.config.get("cache_days", 1):
                return self._load_csv(cache_path)
        
        # Fallback: attempt to fetch from API
        try:
            data = self.client.daily_adjusted(symbol)
            df = self._parse_av_response(data, symbol)
            
            if df is not None and len(df) > 0:
                self._save_csv(df, cache_path)
                return df
        except Exception as e:
            print(f"API fetch failed for {symbol}: {e}")
        
        # Last resort: try CSV cache anyway (even if older)
        if cache_path.exists():
            return self._load_csv(cache_path)
        
        # Try manual directory
        manual_path = MANUAL_DIR / f"{symbol}.csv"
        if manual_path.exists():
            return self._load_csv(manual_path)
        
        return None
    
    def _parse_av_response(self, data: dict, symbol: str) -> Optional[pd.DataFrame]:
        """Parse Alpha Vantage JSON response."""
        ts_key = "Time Series (Daily Adjusted)"
        if ts_key not in data:
            return None
        
        ts = data[ts_key]
        records = []
        
        for date_str, values in ts.items():
            try:
                record = {
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": int(float(values["6. volume"])),
                }
                records.append((datetime.strptime(date_str, "%Y-%m-%d"), record))
            except:
                pass
        
        if not records:
            return None
        
        # Sort by date
        records.sort(key=lambda x: x[0])
        
        df = pd.DataFrame([r[1] for r in records], index=[r[0] for r in records])
        df.index.name = "date"
        
        return df[OHLCV_COLS]
    
    def _load_csv(self, path: Path) -> Optional[pd.DataFrame]:
        """Carica CSV da cache."""
        try:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            return df[OHLCV_COLS] if all(c in df.columns for c in OHLCV_COLS) else None
        except:
            return None
    
    def _save_csv(self, df: pd.DataFrame, path: Path) -> None:
        """Salva CSV in cache."""
        try:
            df.to_csv(path)
        except:
            pass


# ==================== SYNTHETIC DATA ====================

def generate_synthetic(ticker: str,
                      n_bars: int = 504,
                      trend: str = "up",
                      volatility: float = 0.02,
                      seed: int = None) -> pd.DataFrame:
    """
    Genera dati sintetici per testing.
    
    Args:
        ticker: simbolo
        n_bars: numero di barre
        trend: "up", "down", "random"
        volatility: volatilità simulata (default 2%)
        seed: per riproducibilità
    
    Returns:
        DataFrame OHLCV
    """
    if seed:
        np.random.seed(seed)
    
    close_prices = [100.0]
    
    if trend == "up":
        drift = 0.0005  # +0.05% per bar
    elif trend == "down":
        drift = -0.0005
    else:
        drift = 0.0
    
    for _ in range(n_bars - 1):
        change = drift + np.random.normal(0, volatility)
        close_prices.append(close_prices[-1] * (1 + change))
    
    close_prices = np.array(close_prices)
    
    # Genera OHLC dai close
    opens = close_prices + np.random.normal(0, volatility * close_prices, n_bars)
    highs = np.maximum(close_prices, opens) + np.abs(np.random.normal(0, volatility * close_prices, n_bars))
    lows = np.minimum(close_prices, opens) - np.abs(np.random.normal(0, volatility * close_prices, n_bars))
    volumes = np.random.uniform(1_000_000, 5_000_000, n_bars)
    
    dates = pd.date_range(end=datetime.now(), periods=n_bars, freq="D")
    
    df = pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": close_prices,
        "volume": volumes.astype(int),
    }, index=dates)
    
    return df[OHLCV_COLS]


# ==================== UTILITIES ====================

def get_sp500_subset(sectors: List[str] = None) -> List[str]:
    """Ritorna lista ticker da settori."""
    if sectors is None:
        sectors = list(SP500_SUBSET.keys())
    
    tickers = []
    for sector in sectors:
        if sector in SP500_SUBSET:
            tickers.extend(SP500_SUBSET[sector])
    
    return list(set(tickers))  # Remove duplicates


def ensure_min_history(df: pd.DataFrame, min_bars: int = 252) -> bool:
    """Verifica se DataFrame ha abbastanza dati."""
    return len(df) >= min_bars


def resample_to_weekly(df_daily: pd.DataFrame) -> pd.DataFrame:
    """Resamples daily to weekly."""
    return df_daily.resample("W").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()


# ==================== CACHE UTILITIES ====================

def clear_cache(symbol: str = None) -> None:
    """Cancella cache per un simbolo o tutto."""
    if symbol:
        path = CACHE_DIR / f"{symbol}.csv"
        if path.exists():
            path.unlink()
    else:
        for path in CACHE_DIR.glob("*.csv"):
            path.unlink()


def get_cache_age(symbol: str) -> Optional[int]:
    """Ritorna età cache in giorni."""
    path = CACHE_DIR / f"{symbol}.csv"
    if not path.exists():
        return None
    
    age = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days
    return age


def cache_info() -> Dict:
    """Info su cache."""
    if not CACHE_DIR.exists():
        return {"count": 0, "symbols": []}
    
    files = list(CACHE_DIR.glob("*.csv"))
    symbols = [f.stem for f in files]
    ages = {s: get_cache_age(s) for s in symbols}
    
    return {
        "count": len(symbols),
        "symbols": symbols,
        "ages_days": ages,
    }
