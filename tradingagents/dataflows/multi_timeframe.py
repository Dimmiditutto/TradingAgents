"""
Multi-Timeframe Data Layer - Weekly + Daily with Confluence

Architecture:
  Weekly: Macro trend + structural levels
  Daily: Operational signals + precise entry/exit
  
Constraint: 25 API calls/day on Alpha Vantage FREE
Solution: Dual TF = 2 calls per symbol (not 3-4 with intraday)
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from .cache_manager import CacheManager
from .technical_calculations import get_all_indicators


@dataclass
class TimeframeData:
    """Container for single-timeframe OHLCV + indicators"""
    symbol: str
    timeframe: str  # 'daily' or 'weekly'
    ohlcv: pd.DataFrame  # OHLCV data
    indicators: Dict  # All calculated indicators
    last_update: datetime
    
    def latest(self, indicator_name: str, offset: int = 0):
        """Get latest value of an indicator (offset=0 is latest, 1 is prev bar)"""
        if indicator_name not in self.indicators:
            return None
        
        series = self.indicators[indicator_name]
        if offset >= len(series):
            return None
        
        return series.iloc[-1 - offset]


@dataclass
class MultiTimeframeData:
    """Container for weekly + daily synchronized data"""
    symbol: str
    daily: TimeframeData
    weekly: TimeframeData
    sync_date: datetime
    
    def __post_init__(self):
        """Ensure weekly and daily are synchronized to same end date"""
        # Find common date that exists in both
        daily_dates = set(self.daily.ohlcv['date'].dt.date)
        weekly_dates = set(self.weekly.ohlcv['date'].dt.date)
        common_dates = daily_dates & weekly_dates
        
        if not common_dates:
            # If no exact match, use most recent from daily that's before weekly's last
            daily_last = self.daily.ohlcv['date'].max().date()
            weekly_last = self.weekly.ohlcv['date'].max().date()
            self.sync_date = min(daily_last, weekly_last)
        else:
            self.sync_date = max(common_dates)


class MultiTimeframeLayer:
    """Manage Weekly + Daily data with intelligent caching"""
    
    def __init__(self, cache_dir: str = "./data_cache"):
        """Initialize MTF layer with cache manager"""
        self.cache_mgr = CacheManager(cache_dir)
        self.mtf_cache = {}  # In-memory cache of (weekly, daily) pairs
    
    def fetch_symbol_mtf(
        self,
        symbol: str,
        end_date: datetime = None,
        start_date_daily: datetime = None,
        start_date_weekly: datetime = None,
        force_refresh: bool = False
    ) -> MultiTimeframeData:
        """
        Fetch synchronized weekly + daily data for symbol
        
        Args:
            symbol: Ticker symbol
            end_date: End date for both TF (default: today)
            start_date_daily: Start for daily (default: 1 year ago)
            start_date_weekly: Start for weekly (default: 5 years ago)
            force_refresh: Force fetch even if cached
        
        Returns:
            MultiTimeframeData with weekly + daily + indicators
        
        Cost: 2 API calls per symbol (1 daily, 1 weekly)
        """
        if end_date is None:
            end_date = datetime.now()
        
        if start_date_daily is None:
            start_date_daily = end_date - timedelta(days=365)
        
        if start_date_weekly is None:
            start_date_weekly = end_date - timedelta(days=365*5)
        
        # Fetch daily
        daily_data = self._fetch_timeframe(
            symbol, "daily",
            start=start_date_daily, end=end_date,
            force_refresh=force_refresh
        )
        
        # Fetch weekly
        weekly_data = self._fetch_timeframe(
            symbol, "weekly",
            start=start_date_weekly, end=end_date,
            force_refresh=force_refresh
        )
        
        # Create MTF container
        mtf = MultiTimeframeData(
            symbol=symbol,
            daily=daily_data,
            weekly=weekly_data,
            sync_date=datetime.now()
        )
        
        # Cache in memory
        self.mtf_cache[symbol] = mtf
        
        return mtf
    
    def _fetch_timeframe(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        force_refresh: bool = False
    ) -> TimeframeData:
        """Fetch single timeframe (daily or weekly) with smart caching"""
        
        def fetch_and_process():
            """Fetch from yfinance and process"""
            interval = "1d" if timeframe == "daily" else "1wk"
            
            # Fetch from yfinance
            df = yf.download(
                symbol,
                start=start,
                end=end,
                interval=interval,
                progress=False,
                auto_adjust=True
            )
            
            if df.empty:
                raise ValueError(f"No data for {symbol} on {timeframe}")
            
            df = df.reset_index()
            df.columns = df.columns.str.lower()
            
            # Rename yfinance columns to standard
            rename_map = {
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'adj close': 'close'  # Handle adjusted close
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            
            # Ensure required columns
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
            # Return: (full_data, new_rows for cache)
            return df, df
        
        # Use cache manager for smart updates
        ohlcv = self.cache_mgr.get_cached_or_fetch(
            f"{symbol}_{timeframe}",
            fetch_and_process,
            timeframe=timeframe,
            force_refresh=force_refresh
        )
        
        # Calculate all indicators for this timeframe
        indicators = get_all_indicators(ohlcv, swing_mode=True)
        
        return TimeframeData(
            symbol=symbol,
            timeframe=timeframe,
            ohlcv=ohlcv,
            indicators=indicators,
            last_update=datetime.now()
        )
    
    def get_cached_mtf(self, symbol: str) -> Optional[MultiTimeframeData]:
        """Get cached MTF data if available"""
        return self.mtf_cache.get(symbol)
    
    def confluence_check_long(self, mtf: MultiTimeframeData) -> Tuple[bool, str]:
        """
        Check if setup is valid for LONG trade (multi-TF confluence)
        
        Returns:
            (is_valid, reason_string)
        
        Logic:
          LONG valid if:
            ✓ Weekly: close > 200 SMA weekly + structure HH/HL intact
            ✓ Daily: test of swing low + CHoCH or BOS
        """
        reasons = []
        is_valid = True
        
        # Weekly checks
        weekly_close = mtf.weekly.latest('close')
        weekly_200sma = mtf.weekly.latest('close_200_sma')
        weekly_trend = mtf.weekly.latest('supertrend_direction')
        
        if weekly_close is None or weekly_200sma is None:
            return False, "Insufficient weekly data"
        
        if weekly_close > weekly_200sma:
            reasons.append("✓ Weekly: Price > 200 SMA (bull regime)")
        else:
            reasons.append("✗ Weekly: Price < 200 SMA (bear regime - AVOID LONG)")
            is_valid = False
        
        if weekly_trend == 1:
            reasons.append("✓ Weekly: SuperTrend = Uptrend (+1)")
        else:
            reasons.append("✗ Weekly: SuperTrend = Downtrend (-1)")
            is_valid = False
        
        # Daily checks
        daily_adx = mtf.daily.latest('adx')
        daily_er = mtf.daily.latest('er')
        daily_close = mtf.daily.latest('close')
        daily_donchian_h = mtf.daily.latest('donchian_high')
        daily_volume_ratio = mtf.daily.latest('volume_ratio')
        
        if daily_adx is not None and daily_adx > 25:
            reasons.append(f"✓ Daily: ADX = {daily_adx:.1f} (strong trend, >25)")
        elif daily_adx is not None:
            reasons.append(f"✗ Daily: ADX = {daily_adx:.1f} (weak trend, <25)")
            is_valid = False
        
        if daily_er is not None and daily_er > 0.5:
            reasons.append(f"✓ Daily: ER = {daily_er:.2f} (efficient trend, >0.5)")
        elif daily_er is not None:
            reasons.append(f"✗ Daily: ER = {daily_er:.2f} (rangy/choppy)")
            is_valid = False
        
        # Breakout check
        if daily_close is not None and daily_donchian_h is not None:
            if daily_close > daily_donchian_h:
                reasons.append(f"✓ Daily: Price > Donchian High (BOS bullish)")
            else:
                reasons.append(f"→ Daily: Price < Donchian High (no BOS yet)")
        
        # Volume check
        if daily_volume_ratio is not None:
            if daily_volume_ratio > 1.5:
                reasons.append(f"✓ Daily: Volume Ratio = {daily_volume_ratio:.2f} (STRONG BOS)")
            elif daily_volume_ratio > 1.0:
                reasons.append(f"→ Daily: Volume Ratio = {daily_volume_ratio:.2f} (normal)")
            else:
                reasons.append(f"✗ Daily: Volume Ratio = {daily_volume_ratio:.2f} (WEAK BOS)")
        
        return is_valid, "\n".join(reasons)
    
    def confluence_check_short(self, mtf: MultiTimeframeData) -> Tuple[bool, str]:
        """
        Check if setup is valid for SHORT trade (multi-TF confluence)
        
        Returns:
            (is_valid, reason_string)
        
        Logic:
          SHORT valid if:
            ✓ Weekly: close < 200 SMA weekly + structure LH/LL intact
            ✓ Daily: test of swing high + CHoCH or BOS
        """
        reasons = []
        is_valid = True
        
        # Weekly checks
        weekly_close = mtf.weekly.latest('close')
        weekly_200sma = mtf.weekly.latest('close_200_sma')
        weekly_trend = mtf.weekly.latest('supertrend_direction')
        
        if weekly_close is None or weekly_200sma is None:
            return False, "Insufficient weekly data"
        
        if weekly_close < weekly_200sma:
            reasons.append("✓ Weekly: Price < 200 SMA (bear regime)")
        else:
            reasons.append("✗ Weekly: Price > 200 SMA (bull regime - AVOID SHORT)")
            is_valid = False
        
        if weekly_trend == -1:
            reasons.append("✓ Weekly: SuperTrend = Downtrend (-1)")
        else:
            reasons.append("✗ Weekly: SuperTrend = Uptrend (+1)")
            is_valid = False
        
        # Daily checks
        daily_adx = mtf.daily.latest('adx')
        daily_er = mtf.daily.latest('er')
        daily_close = mtf.daily.latest('close')
        daily_donchian_l = mtf.daily.latest('donchian_low')
        daily_volume_ratio = mtf.daily.latest('volume_ratio')
        
        if daily_adx is not None and daily_adx > 25:
            reasons.append(f"✓ Daily: ADX = {daily_adx:.1f} (strong trend, >25)")
        elif daily_adx is not None:
            reasons.append(f"✗ Daily: ADX = {daily_adx:.1f} (weak trend, <25)")
            is_valid = False
        
        if daily_er is not None and daily_er > 0.5:
            reasons.append(f"✓ Daily: ER = {daily_er:.2f} (efficient trend, >0.5)")
        elif daily_er is not None:
            reasons.append(f"✗ Daily: ER = {daily_er:.2f} (rangy/choppy)")
            is_valid = False
        
        # Breakdown check
        if daily_close is not None and daily_donchian_l is not None:
            if daily_close < daily_donchian_l:
                reasons.append(f"✓ Daily: Price < Donchian Low (BOS bearish)")
            else:
                reasons.append(f"→ Daily: Price > Donchian Low (no BOS yet)")
        
        # Volume check
        if daily_volume_ratio is not None:
            if daily_volume_ratio > 1.5:
                reasons.append(f"✓ Daily: Volume Ratio = {daily_volume_ratio:.2f} (STRONG BOS)")
            elif daily_volume_ratio > 1.0:
                reasons.append(f"→ Daily: Volume Ratio = {daily_volume_ratio:.2f} (normal)")
            else:
                reasons.append(f"✗ Daily: Volume Ratio = {daily_volume_ratio:.2f} (WEAK BOS)")
        
        return is_valid, "\n".join(reasons)
    
    def clear_cache(self, symbol: str = None):
        """Clear cache (local CSV and in-memory)"""
        self.cache_mgr.clear_cache(symbol)
        if symbol and symbol in self.mtf_cache:
            del self.mtf_cache[symbol]


# ==================== EXAMPLE USAGE ====================

def example_mtf_confluence():
    """Example: Fetch MTF data and check confluence"""
    
    mtf_layer = MultiTimeframeLayer()
    
    symbols = ["SPY", "QQQ", "AAPL"]
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"📊 Analyzing {symbol} - Multi-Timeframe Confluence")
        print(f"{'='*60}\n")
        
        mtf = mtf_layer.fetch_symbol_mtf(symbol)
        
        # Check LONG
        long_valid, long_reason = mtf_layer.confluence_check_long(mtf)
        print(f"🟢 LONG SETUP: {'✓ VALID' if long_valid else '✗ INVALID'}")
        print(long_reason)
        
        # Check SHORT
        short_valid, short_reason = mtf_layer.confluence_check_short(mtf)
        print(f"\n🔴 SHORT SETUP: {'✓ VALID' if short_valid else '✗ INVALID'}")
        print(short_reason)
        
        # Summary metrics
        print(f"\n📈 Key Metrics:")
        print(f"  Weekly 200 SMA: {mtf.weekly.latest('close_200_sma'):.2f}")
        print(f"  Daily ADX: {mtf.daily.latest('adx'):.1f}")
        print(f"  Daily Volume Ratio: {mtf.daily.latest('volume_ratio'):.2f}")
        print(f"  Sync Date: {mtf.sync_date}")


if __name__ == "__main__":
    example_mtf_confluence()
