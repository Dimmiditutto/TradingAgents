"""
scoring_engine_v2.py - Advanced 5-Component Swing Scoring
Cleaned version with proper error handling and optional mtf_data
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np


# ═════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class SwingSignalV2:
    """Complete swing signal with all components."""
    ticker: str
    timestamp: datetime
    direction: str  # "LONG" or "SHORT"
    score: float  # 0-100
    sub_scores: Dict[str, float]
    filters_passed: bool
    filter_failures: List[str] = field(default_factory=list)
    
    # Price levels
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target1: float = 0.0
    target2: float = 0.0
    
    # Context
    atr: float = 0.0
    atr_pct: float = 0.0
    risk_reward: float = 0.0
    
    weekly_trend: str = "UNDEFINED"
    daily_trend: str = "UNDEFINED"
    structure_event: str = ""
    adx: float = 0.0
    rsi: float = 50.0
    volume_ratio: float = 1.0
    pct_from_200sma: float = 0.0
    
    def to_dict(self) -> Dict:
        """Export as dictionary."""
        d = asdict(self)
        d['timestamp'] = str(d['timestamp'])
        return d


# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

DEFAULT_WEIGHTS = {
    "structure": 0.30,
    "trend": 0.25,
    "momentum": 0.25,
    "volatility": 0.10,
    "volume": 0.10,
}

DEFAULT_FILTERS = {
    "weekly_trend_match": True,
    "above_200sma": True,
    "adx_min": 20.0,
    "supertrend_align": True,
    "atr_pct_min": 0.5,
    "atr_pct_max": 8.0,
    "not_overextended": True,  # not >25% above 200sma
}

DEFAULT_TRADE = {
    "stop_atr_mult": 1.5,
    "target1_atr_mult": 2.0,
    "target2_atr_mult": 3.0,
}


# ═════════════════════════════════════════════════════════════════════════════
# SCORING COMPONENTS
# ═════════════════════════════════════════════════════════════════════════════

def score_structure(df: pd.DataFrame, mtf_data: Dict = None, direction: str = "LONG") -> Tuple[float, Dict]:
    """Score 1/5: Structure (CHoCH/BOS), weight 30%."""
    if mtf_data is None:
        mtf_data = {}
    
    score = 50.0  # Base score
    details = {}
    
    # CHoCH bullish recent
    recent_choch = mtf_data.get("recent_choch", False)
    if recent_choch and direction == "LONG":
        score += 35
        details["choch"] = True
    
    # BOS double
    recent_bos = mtf_data.get("recent_bos", False)
    if recent_bos and direction == "LONG":
        score += 25
        details["bos"] = True
    
    # Weekly trend support
    weekly_trend = mtf_data.get("weekly_trend", "UP")
    if weekly_trend == "UP" and direction == "LONG":
        score += 15
        details["weekly_support"] = True
    
    return min(score, 100.0), details


def score_trend_strength(df: pd.DataFrame, direction: str = "LONG") -> Tuple[float, Dict]:
    """Score 2/5: Trend Strength, weight 25%."""
    score = 50.0
    details = {}
    
    # ADX strength
    adx = df["adx"].iloc[-1] if "adx" in df.columns else 0.0
    if adx >= 35:
        score += 25
        details["adx_strong"] = True
    elif adx >= 20:
        score += 15
        details["adx_moderate"] = True
    
    # Efficiency Ratio
    efr = df["efr"].iloc[-1] if "efr" in df.columns else 0.0
    if efr >= 0.5:
        score += 15
        details["efr_good"] = True
    
    # SuperTrend
    supertrend = df["supertrend"].iloc[-1] if "supertrend" in df.columns else 0.0
    close = df["close"].iloc[-1]
    if direction == "LONG" and close > supertrend:
        score += 20
        details["supertrend_bullish"] = True
    
    # Linear Regression R²
    linreg_r2 = df["linreg_r2"].iloc[-1] if "linreg_r2" in df.columns else 0.0
    if linreg_r2 >= 0.7:
        score += 15
        details["trend_established"] = True
    
    return min(score, 100.0), details


def score_momentum(df: pd.DataFrame, direction: str = "LONG") -> Tuple[float, Dict]:
    """Score 3/5: Momentum, weight 25%."""
    score = 50.0
    details = {}
    
    # RSI
    rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50.0
    if 40 <= rsi <= 60:  # Not overextended
        score += 15
        details["rsi_neutral"] = True
    
    # TSI
    tsi = df["tsi"].iloc[-1] if "tsi" in df.columns else 0.0
    tsi_signal = df["tsi_signal"].iloc[-1] if "tsi_signal" in df.columns else 0.0
    if direction == "LONG" and tsi > tsi_signal:
        score += 15
        details["tsi_bullish"] = True
    
    # MACD
    macd_hist = df["macd_histogram"].iloc[-1] if "macd_histogram" in df.columns else 0.0
    macd_slope = (df["macd_histogram"].iloc[-1] - df["macd_histogram"].iloc[-2]) if len(df) >= 2 else 0.0
    if direction == "LONG" and macd_hist > 0 and macd_slope > 0:
        score += 20
        details["macd_bullish"] = True
    
    # MFI/Volume
    mfi = df["mfi"].iloc[-1] if "mfi" in df.columns else 50.0
    if direction == "LONG" and mfi > 50:
        score += 10
        details["mfi_bullish"] = True
    
    return min(score, 100.0), details


def score_volatility(df: pd.DataFrame) -> Tuple[float, Dict]:
    """Score 4/5: Volatility, weight 10%."""
    score = 50.0
    details = {}
    
    # Bollinger %B
    boll_pct = df["boll_pct"].iloc[-1] if "boll_pct" in df.columns else 0.5
    if 0.2 <= boll_pct <= 0.8:  # Not at extremes
        score += 30
        details["bands_neutral"] = True
    
    # Bandwidth expanding
    boll_bw = df["boll_bandwidth"].iloc[-1] if "boll_bandwidth" in df.columns else 0.0
    boll_bw_prev = df["boll_bandwidth"].iloc[-2] if len(df) >= 2 and "boll_bandwidth" in df.columns else 0.0
    if boll_bw > boll_bw_prev:
        score += 20
        details["expansion"] = True
    
    # Price near midline
    boll_mid = df["boll_middle"].iloc[-1] if "boll_middle" in df.columns else 0.0
    close = df["close"].iloc[-1]
    if abs(close - boll_mid) / (boll_mid + 0.001) < 0.02:
        score += 15
        details["midline_touch"] = True
    
    return min(score, 100.0), details


def score_volume(df: pd.DataFrame, direction: str = "LONG") -> Tuple[float, Dict]:
    """Score 5/5: Volume, weight 10%."""
    score = 50.0
    details = {}
    
    # Volume Ratio
    vol_ratio = df["vol_ratio"].iloc[-1] if "vol_ratio" in df.columns else 1.0
    if vol_ratio >= 1.3:
        score += 25
        details["high_volume"] = True
    
    # MFI confirmation
    mfi = df["mfi"].iloc[-1] if "mfi" in df.columns else 50.0
    vol_ratio_trend = (vol_ratio > df["vol_ratio"].iloc[-2]) if len(df) >= 2 and "vol_ratio" in df.columns else False
    if mfi > 50 and vol_ratio_trend:
        score += 20
        details["vol_aligned"] = True
    
    # Volume SMA
    vol_sma = df["vol_sma"].iloc[-1] if "vol_sma" in df.columns else 0.0
    vol = df["volume"].iloc[-1]
    if vol > vol_sma:
        score += 15
        details["vol_above_sma"] = True
    
    return min(score, 100.0), details


# ═════════════════════════════════════════════════════════════════════════════
# FILTERS
# ═════════════════════════════════════════════════════════════════════════════

def check_filters(df: pd.DataFrame, 
                 mtf_data: Dict = None,
                 direction: str = "LONG",
                 filters: Dict = None) -> Tuple[bool, List[str]]:
    """Check mandatory filters."""
    if filters is None:
        filters = DEFAULT_FILTERS
    if mtf_data is None:
        mtf_data = {}
    
    failures = []
    
    # 1. Weekly trend match
    weekly_trend = mtf_data.get("weekly_trend", "UP")
    if filters.get("weekly_trend_match", True):
        if direction == "LONG" and weekly_trend != "UP":
            failures.append("Weekly trend not bullish")
        elif direction == "SHORT" and weekly_trend != "DOWN":
            failures.append("Weekly trend not bearish")
    
    # 2. Above 200 SMA
    if filters.get("above_200sma", True):
        sma200 = df["sma_200"].iloc[-1] if "sma_200" in df.columns else 0.0
        close = df["close"].iloc[-1]
        if direction == "LONG" and close < sma200:
            failures.append("Price below SMA200")
    
    # 3. ADX minimum
    adx_min = filters.get("adx_min", 20.0)
    adx = df["adx"].iloc[-1] if "adx" in df.columns else 0.0
    if adx < adx_min:
        failures.append(f"ADX too low: {adx:.1f}<{adx_min}")
    
    # 4. SuperTrend alignment
    if filters.get("supertrend_align", True):
        supertrend = df["supertrend"].iloc[-1] if "supertrend" in df.columns else 0.0
        close = df["close"].iloc[-1]
        if direction == "LONG" and close < supertrend:
            failures.append("SuperTrend bearish")
    
    # 5. ATR% range
    atr_pct_min = filters.get("atr_pct_min", 0.5)
    atr_pct_max = filters.get("atr_pct_max", 8.0)
    atr_pct = df["atr_pct"].iloc[-1] if "atr_pct" in df.columns else 1.0
    if not (atr_pct_min <= atr_pct <= atr_pct_max):
        failures.append(f"ATR% out of range: {atr_pct:.2f}%")
    
    # 6. Not overextended
    if filters.get("not_overextended", True):
        pct_from_200 = df["pct_from_200sma"].iloc[-1] if "pct_from_200sma" in df.columns else 0.0
        if direction == "LONG" and pct_from_200 > 25:
            failures.append(f"Overextended: {pct_from_200:.1f}% above SMA200")
    
    return (len(failures) == 0), failures


# ═════════════════════════════════════════════════════════════════════════════
# PRICE LEVELS
# ═════════════════════════════════════════════════════════════════════════════

def calculate_levels(df: pd.DataFrame, 
                    direction: str = "LONG",
                    atr: float = 1.0,
                    trade_params: Dict = None) -> Tuple[float, float, float]:
    """Calculate entry, stop, target levels."""
    if trade_params is None:
        trade_params = DEFAULT_TRADE
    
    entry = df["close"].iloc[-1]
    
    stop_mult = trade_params.get("stop_atr_mult", 1.5)
    target_mult = trade_params.get("target1_atr_mult", 2.0)
    
    if direction == "LONG":
        stop = entry - stop_mult * atr
        target = entry + target_mult * atr
    else:
        stop = entry + stop_mult * atr
        target = entry - target_mult * atr
    
    return entry, stop, target


# ═════════════════════════════════════════════════════════════════════════════
# MAIN SCORING FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def score_signal(ticker: str,
                df: pd.DataFrame,
                direction: str = "LONG",
                mtf_data: Dict = None,
                weights: Dict = None,
                filters: Dict = None,
                trade_params: Dict = None,
                min_score: float = 70.0) -> Optional[SwingSignalV2]:
    """
    Score a single direction signal.
    
    Returns SwingSignalV2 if all filters pass and score >= min_score, else None.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    if filters is None:
        filters = DEFAULT_FILTERS
    if trade_params is None:
        trade_params = DEFAULT_TRADE
    if mtf_data is None:
        mtf_data = {}
    
    # Check filters first
    filters_passed, failures = check_filters(df, mtf_data, direction, filters)
    
    if not filters_passed:
        return None
    
    # Calculate component scores
    s1, d1 = score_structure(df, mtf_data, direction)
    s2, d2 = score_trend_strength(df, direction)
    s3, d3 = score_momentum(df, direction)
    s4, d4 = score_volatility(df)
    s5, d5 = score_volume(df, direction)
    
    # Weighted total
    score = (s1 * weights["structure"] +
             s2 * weights["trend"] +
             s3 * weights["momentum"] +
             s4 * weights["volatility"] +
             s5 * weights["volume"])
    
    # Below minimum threshold
    if score < min_score:
        return None
    
    # Get ATR for levels
    atr = df["atr"].iloc[-1] if "atr" in df.columns else 1.0
    atr_pct = df["atr_pct"].iloc[-1] if "atr_pct" in df.columns else 1.0
    entry, stop, target = calculate_levels(df, direction, atr, trade_params)
    risk_reward = abs(target - entry) / (abs(entry - stop) + 0.0001)
    
    # Build signal
    signal = SwingSignalV2(
        ticker=ticker,
        timestamp=df.index[-1],
        direction=direction,
        score=score,
        sub_scores={
            "structure": s1,
            "trend": s2,
            "momentum": s3,
            "volatility": s4,
            "volume": s5,
        },
        filters_passed=True,
        filter_failures=[],
        entry_price=entry,
        stop_loss=stop,
        target1=target,
        atr=atr,
        atr_pct=atr_pct,
        risk_reward=risk_reward,
        weekly_trend=mtf_data.get("weekly_trend", "UNDEFINED"),
        daily_trend=mtf_data.get("daily_trend", "UNDEFINED"),
        structure_event=mtf_data.get("structure_event", ""),
        adx=df["adx"].iloc[-1] if "adx" in df.columns else 0.0,
        rsi=df["rsi"].iloc[-1] if "rsi" in df.columns else 50.0,
        volume_ratio=df["vol_ratio"].iloc[-1] if "vol_ratio" in df.columns else 1.0,
        pct_from_200sma=df["pct_from_200sma"].iloc[-1] if "pct_from_200sma" in df.columns else 0.0,
    )
    
    return signal


def score_both_directions(ticker: str,
                         df: pd.DataFrame,
                         mtf_data: Dict = None,
                         weights: Dict = None,
                         filters: Dict = None,
                         trade_params: Dict = None,
                         min_score: float = 70.0) -> List[Optional[SwingSignalV2]]:
    """Score both LONG and SHORT directions."""
    if mtf_data is None:
        mtf_data = {}
    
    results = []
    
    for direction in ["LONG", "SHORT"]:
        signal = score_signal(
            ticker, df, direction, mtf_data,
            weights, filters, trade_params, min_score
        )
        results.append(signal)
    
    return results
