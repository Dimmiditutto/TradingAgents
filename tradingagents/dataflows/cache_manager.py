"""
Cache Manager - Smart Local Data Caching

Gestisce i CSV locali e aggiorna SOLO i dati nuovi (ultima barra)
Per ottimizzare i 25 API calls/giorno su Alpha Vantage FREE

Key insight: I dati di ieri su daily NON CAMBIANO
- Cache existing data, fetch only TODAY's candle
- Per 12 ticker: 12 calls instead of 24 (1 call per ticker, not 2×12)
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, Optional
from pathlib import Path


class CacheManager:
    """Manage local CSV caches with smart incremental updates"""
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory to store CSV caches. Default: ./data_cache
        """
        if cache_dir is None:
            cache_dir = os.path.join(os.getcwd(), "data_cache")
        
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # Log file for tracking API calls
        self.log_file = os.path.join(cache_dir, "cache_operations.log")
    
    def _log(self, message: str):
        """Log cache operations for tracking API usage"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(self.log_file, "a") as f:
            f.write(log_entry)
    
    def _get_cache_path(self, symbol: str, timeframe: str = "daily") -> str:
        """Get the path for a symbol's cache file"""
        filename = f"{symbol.upper()}_{timeframe}.csv"
        return os.path.join(self.cache_dir, filename)
    
    def has_cache(self, symbol: str, timeframe: str = "daily") -> bool:
        """Check if cache exists for a symbol"""
        cache_path = self._get_cache_path(symbol, timeframe)
        return os.path.exists(cache_path)
    
    def get_last_cached_date(self, symbol: str, timeframe: str = "daily") -> Optional[datetime]:
        """
        Get the last date in the cache
        
        Returns:
            datetime of last cached bar, or None if no cache
        """
        if not self.has_cache(symbol, timeframe):
            return None
        
        cache_path = self._get_cache_path(symbol, timeframe)
        try:
            df = pd.read_csv(cache_path)
            if df.empty:
                return None
            
            last_date_str = df.iloc[-1]['date'] if 'date' in df.columns else df.index[-1]
            return pd.to_datetime(last_date_str)
        except Exception as e:
            self._log(f"ERROR reading cache for {symbol}: {e}")
            return None
    
    def should_update(self, symbol: str, timeframe: str = "daily") -> bool:
        """
        Check if cache needs update (is last cached date < today?)
        
        Returns:
            True if update needed, False if cache is current
        """
        if not self.has_cache(symbol, timeframe):
            return True  # No cache, need full fetch
        
        last_cached = self.get_last_cached_date(symbol, timeframe)
        if last_cached is None:
            return True
        
        today = datetime.now().date()
        last_cached_date = last_cached.date()
        
        # For daily: if last_cached is older than today, update needed
        if timeframe == "daily":
            # If last bar is > 1 day old, fetch update
            days_old = (today - last_cached_date).days
            return days_old >= 1
        
        # For weekly: if last_cached is older than start of this week
        elif timeframe == "weekly":
            today_weekday = today.weekday()  # 0=Monday, 4=Friday
            start_of_week = today - timedelta(days=today_weekday)
            return last_cached_date < start_of_week
        
        return False
    
    def read_cache(self, symbol: str, timeframe: str = "daily") -> Optional[pd.DataFrame]:
        """
        Read cached data from CSV
        
        Returns:
            DataFrame if cache exists, None otherwise
        """
        if not self.has_cache(symbol, timeframe):
            return None
        
        cache_path = self._get_cache_path(symbol, timeframe)
        try:
            df = pd.read_csv(cache_path)
            df['date'] = pd.to_datetime(df['date'])
            self._log(f"READ cache {symbol}_{timeframe}: {len(df)} rows")
            return df
        except Exception as e:
            self._log(f"ERROR reading cache {symbol}_{timeframe}: {e}")
            return None
    
    def write_cache(self, symbol: str, df: pd.DataFrame, timeframe: str = "daily"):
        """
        Write data to cache CSV
        
        Args:
            symbol: Stock symbol
            df: DataFrame with OHLCV data (must have 'date' column)
            timeframe: 'daily' or 'weekly'
        """
        if df.empty:
            self._log(f"SKIP empty DataFrame for {symbol}_{timeframe}")
            return
        
        cache_path = self._get_cache_path(symbol, timeframe)
        try:
            # Ensure date column is first
            df = df.copy()
            if 'date' in df.columns:
                cols = ['date'] + [c for c in df.columns if c != 'date']
                df = df[cols]
            
            df.to_csv(cache_path, index=False)
            self._log(f"WRITE cache {symbol}_{timeframe}: {len(df)} rows")
        except Exception as e:
            self._log(f"ERROR writing cache {symbol}_{timeframe}: {e}")
    
    def append_to_cache(self, symbol: str, new_data: pd.DataFrame, timeframe: str = "daily"):
        """
        Append new data to existing cache (merge old + new, remove duplicates)
        
        Args:
            symbol: Stock symbol
            new_data: New OHLCV data to append
            timeframe: 'daily' or 'weekly'
        """
        if new_data.empty:
            self._log(f"SKIP empty new data for {symbol}_{timeframe}")
            return
        
        # Read existing cache
        existing = self.read_cache(symbol, timeframe)
        
        if existing is None:
            # No existing cache, just write new data
            self.write_cache(symbol, new_data, timeframe)
            return
        
        # Merge: ensure 'date' columns are datetime
        existing['date'] = pd.to_datetime(existing['date'])
        new_data['date'] = pd.to_datetime(new_data['date'])
        
        # Combine and remove duplicates (keep most recent)
        combined = pd.concat([existing, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=['date'], keep='last')
        combined = combined.sort_values('date').reset_index(drop=True)
        
        self.write_cache(symbol, combined, timeframe)
        self._log(f"APPEND {symbol}_{timeframe}: {len(new_data)} rows added, total {len(combined)}")
    
    def get_cached_or_fetch(
        self,
        symbol: str,
        fetch_fn,
        timeframe: str = "daily",
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Get data from cache OR fetch if needed
        
        Args:
            symbol: Stock symbol
            fetch_fn: Function to call if cache needs update. 
                      Should return (full_df, new_rows_df) tuple
            timeframe: 'daily' or 'weekly'
            force_refresh: Force fetch even if cache is current
        
        Returns:
            Complete DataFrame (cached + any new data)
        
        Example:
            def fetch_spy(symbol):
                df = yf.download(symbol, start='2024-01-01', end=today)
                return df, df  # (full, new)
            
            data = cache_mgr.get_cached_or_fetch("SPY", fetch_spy)
        """
        # If cache is current and user doesn't force refresh, return cached
        if not force_refresh and self.has_cache(symbol, timeframe) and not self.should_update(symbol, timeframe):
            cached = self.read_cache(symbol, timeframe)
            if cached is not None:
                self._log(f"HIT cache {symbol}_{timeframe}: returning {len(cached)} cached rows")
                return cached
        
        # Need to fetch: either no cache, or cache is stale
        self._log(f"MISS/STALE cache {symbol}_{timeframe}: fetching via {fetch_fn.__name__}")
        
        full_df, new_rows = fetch_fn(symbol)
        
        if not new_rows.empty and self.has_cache(symbol, timeframe):
            # Append new rows to existing cache
            self.append_to_cache(symbol, new_rows, timeframe)
        else:
            # Write full data (either first fetch or force_refresh)
            self.write_cache(symbol, full_df, timeframe)
        
        return full_df
    
    def get_cache_stats(self) -> dict:
        """Get statistics about cache usage"""
        cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.csv')]
        stats = {
            'total_files': len(cache_files),
            'symbols': list(set([f.split('_')[0] for f in cache_files])),
            'cache_size_mb': sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files) / (1024*1024),
            'log_file': self.log_file
        }
        return stats
    
    def clear_cache(self, symbol: str = None, timeframe: str = None):
        """
        Clear cache files
        
        Args:
            symbol: If specified, clear only this symbol. If None, clear all.
            timeframe: If specified, clear only this timeframe.
        """
        if symbol is None:
            # Clear all
            for f in os.listdir(self.cache_dir):
                if f.endswith('.csv'):
                    os.remove(os.path.join(self.cache_dir, f))
            self._log("CLEAR all cache files")
        else:
            # Clear specific symbol
            cache_path = self._get_cache_path(symbol, timeframe or "daily")
            if os.path.exists(cache_path):
                os.remove(cache_path)
                self._log(f"CLEAR {symbol}_{timeframe or 'all'}")


# ==================== EXAMPLE USAGE ====================

def example_usage():
    """Example of how to use CacheManager with yfinance"""
    import yfinance as yf
    from datetime import datetime
    
    cache_mgr = CacheManager(cache_dir="./data_cache")
    
    def fetch_yfinance_incremental(symbol: str, timeframe: str = "1d") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch from yfinance with smart incremental updates
        
        Returns (full_df, new_rows):
            - full_df: All available history
            - new_rows: Only new rows added since last cache
        """
        # Get last cached date
        last_cached = cache_mgr.get_last_cached_date(symbol, "daily")
        
        if last_cached:
            # Fetch from (last_cached - 5 days) to today (overlap for safety)
            start_date = last_cached - timedelta(days=5)
            new_data = yf.download(symbol, start=start_date, progress=False)
            
            # All data: return full history (yfinance handles this)
            full_data = yf.download(symbol, start='2015-01-01', progress=False)
        else:
            # First fetch: get 10+ years
            full_data = yf.download(symbol, start='2015-01-01', progress=False)
            new_data = full_data
        
        full_data = full_data.reset_index()
        new_data = new_data.reset_index()
        
        return full_data, new_data
    
    # Usage
    print("Fetching SPY with smart caching...")
    data = cache_mgr.get_cached_or_fetch(
        "SPY",
        fetch_yfinance_incremental,
        timeframe="daily"
    )
    
    print(f"Retrieved {len(data)} rows")
    print(f"\nCache stats: {cache_mgr.get_cache_stats()}")


if __name__ == "__main__":
    example_usage()
