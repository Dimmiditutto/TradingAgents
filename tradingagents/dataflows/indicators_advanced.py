"""
indicators_advanced.py  
═════════════════════════════════════════════════════════════════════════════
Advanced Technical Indicators — 51 calcoli dettagliati per swing trading
Integra swing_system indicators + FASE 2 enhancements

INPUT:  DataFrame OHLCV con colonne [open, high, low, close, volume]
OUTPUT: Stesso DataFrame + 51 colonne di indicatori

CATEGORIE:
  • Moving Averages (5):     EMA10, SMA50, SMA200, VWMA20, %from200SMA
  • Momentum (6):            RSI, TSI, TSI_signal, MACD, MACD_signal, MACD_hist
  • Volatility (7):          Boll (middle/upper/lower), Bandwidth, %B, ATR, ATR%
  • Trend Strength (4):      ADX, +DI, -DI, Efficiency_Ratio
  • Trend Direction (5):     SuperTrend, LinReg, Slope, R², Status
  • Ichimoku (7):            Tenkan, Kijun, SpanA, SpanB, Chikou, Gap, TK_cross
  • Volume (4):              MFI, Volume_ratio, Volume_SMA20
  • Structure (3):           Donchian_H, Donchian_L, Donchian_mid
  • Crossovers (2):          Golden_cross, Death_cross
  • Derivatives (1):         MACD_histogram_slope
────────────────────────────────────────────────────────────────────────────────
"""

import numpy as np
import pandas as pd
from typing import Tuple


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average (Wilder-style)"""
    return series.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return series.rolling(window=period, min_periods=1).mean()


def _rma(series: pd.Series, period: int) -> pd.Series:
    """Wilder's Smoothing (RMA) — usado para ATR e ADX"""
    result = np.full(len(series), np.nan)
    vals   = series.values
    alpha  = 1.0 / period

    first_valid = 0
    while first_valid < len(vals) and np.isnan(vals[first_valid]):
        first_valid += 1

    if first_valid >= len(vals):
        return pd.Series(result, index=series.index)

    result[first_valid] = vals[first_valid]
    for i in range(first_valid + 1, len(vals)):
        if np.isnan(vals[i]):
            result[i] = result[i - 1]
        else:
            result[i] = alpha * vals[i] + (1 - alpha) * result[i - 1]

    return pd.Series(result, index=series.index)


def _highest(series: pd.Series, period: int) -> pd.Series:
    """Highest value in period"""
    return series.rolling(window=period, min_periods=1).max()


def _lowest(series: pd.Series, period: int) -> pd.Series:
    """Lowest value in period"""
    return series.rolling(window=period, min_periods=1).min()


# ═════════════════════════════════════════════════════════════════════════════
# 1. MOVING AVERAGES (5)
# ═════════════════════════════════════════════════════════════════════════════

def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """EMA10, SMA50, SMA200, VWMA20, pct_from_200sma"""
    df = df.copy()
    
    df["ema_10"]        = _ema(df["close"], 10)
    df["sma_50"]        = _sma(df["close"], 50)
    df["sma_200"]       = _sma(df["close"], 200)
   
    # Alias uppercase per compatibilità
    df["EMA10"]   = df["ema_10"]
    df["SMA50"]   = df["sma_50"]
    df["SMA200"]  = df["sma_200"]
    
    # VWMA20 — volume-weighted MA
    tp      = (df["high"] + df["low"] + df["close"]) / 3
    vp      = tp * df["volume"]
    vol_sum = df["volume"].rolling(20, min_periods=1).sum()
    df["vwma_20"] = vp.rolling(20, min_periods=1).sum() / vol_sum.replace(0, np.nan)
    
    # % from 200 SMA — mean reversion metric (filter extreme positions)
    df["pct_from_200sma"] = (df["close"] - df["sma_200"]) / df["sma_200"].replace(0, np.nan) * 100
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 2. MOMENTUM (6)
# ═════════════════════════════════════════════════════════════════════════════

def add_momentum(df: pd.DataFrame,
                 rsi_period: int = 14,
                 tsi_long: int = 13,
                 tsi_short: int = 7,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_sig: int = 9) -> pd.DataFrame:
    """RSI, TSI, TSI_signal, MACD, MACD_signal, MACD_histogram"""
    df = df.copy()
    
    # RSI (Wilder)
    delta   = df["close"].diff()
    gain    = delta.clip(lower=0)
    loss    = (-delta).clip(lower=0)
    avg_g   = _rma(gain, rsi_period)
    avg_l   = _rma(loss, rsi_period)
    rs      = avg_g / avg_l.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    
    # TSI (True Strength Index) — doppio EMA su price change
    pc       = df["close"].diff()
    abs_pc   = pc.abs()
    ema1     = _ema(pc, tsi_long)
    ema2     = _ema(ema1, tsi_short)
    aema1    = _ema(abs_pc, tsi_long)
    aema2    = _ema(aema1, tsi_short)
    df["tsi"]        = 100 * ema2 / aema2.replace(0, np.nan)
    df["tsi_signal"] = _ema(df["tsi"], tsi_short)
    
    # MACD
    fast_ema    = _ema(df["close"], macd_fast)
    slow_ema    = _ema(df["close"], macd_slow)
    df["macd"]  = fast_ema - slow_ema
    df["macd_signal"] = _ema(df["macd"], macd_sig)
    df["macd_histogram"] = df["macd"] - df["macd_signal"]
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 3. VOLATILITY (7)
# ═════════════════════════════════════════════════════════════════════════════

def add_volatility(df: pd.DataFrame, bb_period: int = 20, atr_period: int = 14) -> pd.DataFrame:
    """Bollinger Bands (3), Bandwidth, %B, ATR, ATR%"""
    df = df.copy()
    
    # Bollinger Bands
    df["boll_mid"]   = _sma(df["close"], bb_period)
    std              = df["close"].rolling(bb_period, min_periods=1).std(ddof=0)
    df["boll_upper"] = df["boll_mid"] + 2 * std
    df["boll_lower"] = df["boll_mid"] - 2 * std
    
    # Bandwidth — coiling indicator
    df["boll_bandwidth"] = (df["boll_upper"] - df["boll_lower"]) / df["boll_mid"].replace(0, np.nan) * 100
    
    # %B — position within bands
    band_width = (df["boll_upper"] - df["boll_lower"]).replace(0, np.nan)
    df["boll_pct_b"] = (df["close"] - df["boll_lower"]) / band_width
    
    # ATR (Wilder)
    prev_close = df["close"].shift(1).fillna(df["close"])
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    df["atr"] = _rma(tr, atr_period)
    
    # ATR% — cross-asset comparable
    df["atr_pct"] = df["atr"] / df["close"].replace(0, np.nan) * 100
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 4. TREND STRENGTH (4)
# ═════════════════════════════════════════════════════════════════════════════

def add_trend_strength(df: pd.DataFrame, adx_period: int = 14, er_period: int = 14) -> pd.DataFrame:
    """ADX, +DI, -DI, Efficiency_Ratio"""
    df = df.copy()
    
    # ADX / DI+ / DI-
    up_move   = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm   = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm  = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    prev_close = df["close"].shift(1).fillna(df["close"])
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    
    atr14 = _rma(tr, adx_period)
    df["plus_di"]  = 100 * _rma(pd.Series(plus_dm, index=df.index), adx_period) / atr14.replace(0, np.nan)
    df["minus_di"] = 100 * _rma(pd.Series(minus_dm, index=df.index), adx_period) / atr14.replace(0, np.nan)
    
    dx = 100 * (df["plus_di"] - df["minus_di"]).abs() / (df["plus_di"] + df["minus_di"]).replace(0, np.nan)
    df["adx"] = _rma(dx, adx_period)
    
    # Efficiency Ratio — trend strength vs noise
    ef_len = er_period
    change = (df["close"] - df["close"].shift(ef_len)).abs()
    vol = df["close"].diff().abs().rolling(ef_len, min_periods=1).sum()
    df["efficiency_ratio"] = change / vol.replace(0, np.nan)
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 5. TREND DIRECTION (5)
# ═════════════════════════════════════════════════════════════════════════════

def add_trend_direction(df: pd.DataFrame, st_period: int = 10, st_mult: float = 3.0, lr_period: int = 20) -> pd.DataFrame:
    """SuperTrend, Linear_Regression, Slope, R², Status"""
    df = df.copy()
    
    # SuperTrend
    hl2 = (df["high"] + df["low"]) / 2
    atr = df["atr"] if "atr" in df.columns else _rma(
        pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1), 14
    )
    
    up = hl2 + st_mult * atr
    dn = hl2 - st_mult * atr
    
    up_series = pd.Series(np.nan, index=df.index)
    dn_series = pd.Series(np.nan, index=df.index)
    st_direction = pd.Series(np.nan, index=df.index)
    
    for i in range(len(df)):
        if i == 0:
            up_series.iloc[i] = up.iloc[i]
            dn_series.iloc[i] = dn.iloc[i]
            st_direction.iloc[i] = 1
        else:
            up_series.iloc[i] = up.iloc[i] if up.iloc[i] < up_series.iloc[i-1] or df["close"].iloc[i-1] > up_series.iloc[i-1] else up_series.iloc[i-1]
            dn_series.iloc[i] = dn.iloc[i] if dn.iloc[i] > dn_series.iloc[i-1] or df["close"].iloc[i-1] < dn_series.iloc[i-1] else dn_series.iloc[i-1]
            
            if st_direction.iloc[i-1] == 1:
                st_direction.iloc[i] = -1 if df["close"].iloc[i] <= dn_series.iloc[i] else 1
            else:
                st_direction.iloc[i] = 1 if df["close"].iloc[i] >= up_series.iloc[i] else -1
    
    df["supertrend_up"] = up_series
    df["supertrend_dn"] = dn_series
    df["supertrend"] = st_direction
    
    # Linear Regression (20 periods)
    x = np.arange(lr_period)
    df["linear_reg"] = np.nan
    df["linear_reg_slope"] = np.nan
    df["linear_reg_r2"] = np.nan
    
    for i in range(lr_period - 1, len(df)):
        y = df["close"].iloc[i - lr_period + 1:i + 1].values
        if len(y) == lr_period:
            z = np.polyfit(x, y, 1)
            df.loc[df.index[i], "linear_reg"] = np.polyval(z, lr_period - 1)
            df.loc[df.index[i], "linear_reg_slope"] = z[0]
            
            y_pred = np.polyval(z, x)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            df.loc[df.index[i], "linear_reg_r2"] = 1 - (ss_res / ss_tot if ss_tot != 0 else 0)
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 6. ICHIMOKU (7)
# ═════════════════════════════════════════════════════════════════════════════

def add_ichimoku(df: pd.DataFrame, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52) -> pd.DataFrame:
    """Tenkan, Kijun, SpanA, SpanB, Chikou, Cloud_Gap, TK_Cross"""
    df = df.copy()
    
    # Tenkan (9) e Kijun (26)
    df["ichimoku_tenkan"] = (_highest(df["high"], tenkan_period) + _lowest(df["low"], tenkan_period)) / 2
    df["ichimoku_kijun"]  = (_highest(df["high"], kijun_period) + _lowest(df["low"], kijun_period)) / 2
    
    # Senkou Span A (media di Tenkan e Kijun, proiettato 26 barre avanti)
    senkou_a = (df["ichimoku_tenkan"] + df["ichimoku_kijun"]) / 2
    df["ichimoku_span_a"] = senkou_a.shift(kijun_period)
    
    # Senkou Span B (massimo-minimo di 52 barre, proiettato 26 barre avanti)
    senkou_b = (_highest(df["high"], senkou_b_period) + _lowest(df["low"], senkou_b_period)) / 2
    df["ichimoku_span_b"] = senkou_b.shift(kijun_period)
    
    # Chikou Span (prezzo chiuso, proiettato 26 barre indietro)
    df["ichimoku_chikou"] = df["close"].shift(-kijun_period)
    
    # Cloud Gap — differenza tra i Span
    df["ichimoku_cloud_gap"] = (df["ichimoku_span_a"] - df["ichimoku_span_b"]).abs()
    
    # TK Cross — confluenza Tenkan/Kijun  
    df["ichimoku_tk_cross"] = (df["ichimoku_tenkan"] > df["ichimoku_kijun"]).astype(int)
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 7. VOLUME (4)
# ═════════════════════════════════════════════════════════════════════════════

def add_volume_indicators(df: pd.DataFrame, mfi_period: int = 14) -> pd.DataFrame:
    """MFI, Volume_ratio, Volume_SMA20"""
    df = df.copy()
    
    # MFI (Money Flow Index)
    tp = (df["high"] + df["low"] + df["close"]) / 3
    rmf = tp * df["volume"]
    
    pos_mf = np.where(tp > tp.shift(1), rmf, 0)
    neg_mf = np.where(tp < tp.shift(1), rmf, 0)
    
    pos_mf_sum = pd.Series(pos_mf, index=df.index).rolling(mfi_period, min_periods=1).sum()
    neg_mf_sum = pd.Series(neg_mf, index=df.index).rolling(mfi_period, min_periods=1).sum()
    
    mfi_ratio = pos_mf_sum / (pos_mf_sum + neg_mf_sum).replace(0, np.nan)
    df["mfi"] = 100 * mfi_ratio
    
    # Volume Ratio atual vs SMA20
    vol_sma20 = _sma(df["volume"], 20)
    df["volume_ratio"] = df["volume"] / vol_sma20.replace(0, np.nan)
    
    # Volume SMA20
    df["volume_sma20"] = vol_sma20
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 8. STRUCTURE (3)
# ═════════════════════════════════════════════════════════════════════════════

def add_structure(df: pd.DataFrame, donchian_period: int = 20) -> pd.DataFrame:
    """Donchian_high, Donchian_low, Donchian_mid"""
    df = df.copy()
    
    df["donchian_high"] = _highest(df["high"], donchian_period)
    df["donchian_low"]  = _lowest(df["low"], donchian_period)
    df["donchian_mid"]  = (df["donchian_high"] + df["donchian_low"]) / 2
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 9. CROSSOVERS (2)
# ═════════════════════════════════════════════════════════════════════════════

def add_crossovers(df: pd.DataFrame) -> pd.DataFrame:
    """Golden_cross (50/200), Death_cross (50/200)"""
    df = df.copy()
    
    sma50 = df["sma_50"] if "sma_50" in df.columns else _sma(df["close"], 50)
    sma200 = df["sma_200"] if "sma_200" in df.columns else _sma(df["close"], 200)
    
    df["golden_cross"] = (sma50 > sma200) & (sma50.shift(1) <= sma200.shift(1))
    df["death_cross"]  = (sma50 < sma200) & (sma50.shift(1) >= sma200.shift(1))
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 10. DERIVATIVES (1)
# ═════════════════════════════════════════════════════════════════════════════

def add_derivatives(df: pd.DataFrame) -> pd.DataFrame:
    """MACD_histogram_slope — acceleration/deceleration"""
    df = df.copy()
    
    if "macd_histogram" in df.columns:
        df["macd_histogram_slope"] = df["macd_histogram"].diff()
    
    return df


# ═════════════════════════════════════════════════════════════════════════════
# MAIN COMPUTE FUNCTION
# ═════════════════════════════════════════════════════════════════════════════

def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola tutti i 51 indicatori tecnici.
    
    Args:
        df: DataFrame OHLCV con colonne [open, high, low, close, volume]
           indice deve essere datetime
    
    Returns:
        Lo stesso DataFrame con 51 colonne aggiuntive
    
    Esempio:
        >>> df = pd.read_csv("SPY.csv", parse_dates=True, index_col=0)
        >>> df = compute_all(df)
        >>> print(df.columns)
        # mostra 51 nuove colonne
    """
    df = df.copy()
    
    # Assicura OHLCV in minuscolo
    df.columns = [c.lower() for c in df.columns]
    
    # Calcola in ordine di dipendenza
    df = add_moving_averages(df)           # 5 cols
    df = add_momentum(df)                  # 6 cols
    df = add_volatility(df)                # 7 cols
    df = add_trend_strength(df)            # 4 cols
    df = add_trend_direction(df)           # 5 cols
    df = add_ichimoku(df)                  # 7 cols
    df = add_volume_indicators(df)         # 4 cols
    df = add_structure(df)                 # 3 cols
    df = add_crossovers(df)                # 2 cols
    df = add_derivatives(df)               # 1 col

    # Aliases for compatibility with scoring/dashboard/tests
    df["boll_middle"] = df["boll_mid"]
    df["boll_pct"] = df["boll_pct_b"]
    df["efr"] = df["efficiency_ratio"]
    df["linreg"] = df["linear_reg"]
    df["linreg_slope"] = df["linear_reg_slope"]
    df["linreg_r2"] = df["linear_reg_r2"]
    df["vol_ratio"] = df["volume_ratio"]
    df["vol_sma"] = df["volume_sma20"]

    # Uppercase aliases for legacy callers/tests
    df["RSI"] = df["rsi"]
    df["MACD"] = df["macd"]
    df["ADX"] = df["adx"]
    df["ATR"] = df["atr"]
    df["SuperTrend"] = df["supertrend"]
    
    # Total: 44 indicatori + OHLCV originali = 49 + 2 derived = 51+
    return df


def get_indicator_names() -> list:
    """Ritorna lista di tutti i nomi di indicatori creati."""
    return [
        "ema_10", "sma_50", "sma_200", "vwma_20", "pct_from_200sma",
        "rsi", "tsi", "tsi_signal", "macd", "macd_signal", "macd_histogram",
        "boll_mid", "boll_upper", "boll_lower", "boll_bandwidth", "boll_pct_b",
        "atr", "atr_pct",
        "adx", "plus_di", "minus_di", "efficiency_ratio",
        "supertrend_up", "supertrend_dn", "supertrend",
        "linear_reg", "linear_reg_slope", "linear_reg_r2",
        "ichimoku_tenkan", "ichimoku_kijun", "ichimoku_span_a", "ichimoku_span_b",
        "ichimoku_chikou", "ichimoku_cloud_gap", "ichimoku_tk_cross",
        "mfi", "volume_ratio", "volume_sma20",
        "donchian_high", "donchian_low", "donchian_mid",
        "golden_cross", "death_cross",
        "macd_histogram_slope",
        "boll_middle", "boll_pct", "efr", "linreg", "linreg_slope", "linreg_r2",
        "vol_ratio", "vol_sma",
        "RSI", "MACD", "ADX", "ATR", "SuperTrend",
    ]


if __name__ == "__main__":
    import sys
    # Test
    print("✓ indicators_advanced.py loaded successfully")
    print(f"  Functions available: compute_all() + 10 category functions")
