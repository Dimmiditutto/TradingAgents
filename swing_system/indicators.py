"""
indicators.py
─────────────
Calcola tutti gli indicatori tecnici su un DataFrame OHLCV.
Input:  DataFrame con colonne [open, high, low, close, volume]
Output: stesso DataFrame con colonne indicatori aggiunte

Indicatori inclusi (dalla spec + aggiunte):
  Moving Averages : EMA10, SMA50, SMA200, VWMA20
  Momentum        : RSI, TSI, TSI_signal, MACD, MACD_signal, MACD_hist
  Volatility      : Boll middle/upper/lower, Boll_bandwidth, ATR, ATR_pct
  Trend Strength  : ADX, +DI, -DI, Efficiency Ratio
  Trend Direction : SuperTrend, LinReg, LinReg_slope, LinReg_R2
  Ichimoku        : Tenkan, Kijun, SpanA, SpanB, Chikou
  Volume          : MFI, Volume_ratio, Volume_sma20
  Structure       : Donchian_high, Donchian_low, Donchian_mid
  Derived         : Pct_from_200sma, Golden_cross, Death_cross
"""

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=1).mean()

def _rma(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing (RMA) — usato da ATR e ADX."""
    result = np.full(len(series), np.nan)
    vals   = series.values
    alpha  = 1.0 / period

    # Trova il primo indice non-NaN
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


# ──────────────────────────────────────────────────────────────────────────────
# MOVING AVERAGES
# ──────────────────────────────────────────────────────────────────────────────

def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # EMA 10 — short-term momentum
    df["close_10_ema"] = _ema(df["close"], 10)

    # SMA 50 — medium-term trend
    df["close_50_sma"] = _sma(df["close"], 50)

    # SMA 200 — long-term benchmark
    df["close_200_sma"] = _sma(df["close"], 200)

    # VWMA 20 — volume-weighted: rivela se i partecipanti ad alto volume
    # sono allineati con il trend di prezzo
    tp         = (df["high"] + df["low"] + df["close"]) / 3
    vp         = tp * df["volume"]
    vol_sum    = df["volume"].rolling(20, min_periods=1).sum()
    df["vwma"] = vp.rolling(20, min_periods=1).sum() / vol_sum.replace(0, np.nan)

    # Derived: percentuale dalla 200 SMA — per filtrare titoli in
    # territorio di mean-reversion estrema (>+20% = rischio long ridotto)
    df["pct_from_200sma"] = (df["close"] - df["close_200_sma"]) / df["close_200_sma"].replace(0, np.nan) * 100

    # Crossover signals
    df["golden_cross"] = (df["close_50_sma"] > df["close_200_sma"]) & \
                         (df["close_50_sma"].shift(1) <= df["close_200_sma"].shift(1))
    df["death_cross"]  = (df["close_50_sma"] < df["close_200_sma"]) & \
                         (df["close_50_sma"].shift(1) >= df["close_200_sma"].shift(1))

    return df


# ──────────────────────────────────────────────────────────────────────────────
# MOMENTUM
# ──────────────────────────────────────────────────────────────────────────────

def add_momentum(df: pd.DataFrame,
                 rsi_period: int = 14,
                 tsi_long: int = 13,
                 tsi_short: int = 7,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_sig: int = 9) -> pd.DataFrame:
    df = df.copy()

    # ── RSI (Wilder)
    delta  = df["close"].diff()
    gain   = delta.clip(lower=0)
    loss   = (-delta).clip(lower=0)
    avg_g  = _rma(gain, rsi_period)
    avg_l  = _rma(loss, rsi_period)
    rs     = avg_g / avg_l.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # ── TSI (True Strength Index) — doppio EMA su price change
    # Parametri (13/7) più reattivi del default (25/13) per swing 2-5gg
    pc      = df["close"].diff()
    abs_pc  = pc.abs()
    ema1    = _ema(pc, tsi_long)
    ema2    = _ema(ema1, tsi_short)
    aema1   = _ema(abs_pc, tsi_long)
    aema2   = _ema(aema1, tsi_short)
    df["tsi"]        = 100 * ema2 / aema2.replace(0, np.nan)
    df["tsi_signal"] = _ema(df["tsi"], tsi_short)

    # ── MACD
    fast_ema       = _ema(df["close"], macd_fast)
    slow_ema       = _ema(df["close"], macd_slow)
    df["macd"]     = fast_ema - slow_ema
    df["macds"]    = _ema(df["macd"], macd_sig)
    df["macdh"]    = df["macd"] - df["macds"]

    # Slope dell'istogramma (derivata): rileva accelerazione/decelerazione
    df["macdh_slope"] = df["macdh"].diff()

    return df


# ──────────────────────────────────────────────────────────────────────────────
# VOLATILITY
# ──────────────────────────────────────────────────────────────────────────────

def add_volatility(df: pd.DataFrame, bb_period: int = 20, atr_period: int = 14) -> pd.DataFrame:
    df = df.copy()

    # ── Bollinger Bands
    df["boll"]    = _sma(df["close"], bb_period)
    std           = df["close"].rolling(bb_period, min_periods=1).std(ddof=0)
    df["boll_ub"] = df["boll"] + 2 * std
    df["boll_lb"] = df["boll"] - 2 * std

    # Bandwidth: misura la compressione. Bassa = coiling prima di un breakout.
    # Valore < 5% su azioni USA segnala spesso una fase di accumulazione/distribuzione.
    df["boll_bandwidth"] = (df["boll_ub"] - df["boll_lb"]) / df["boll"].replace(0, np.nan) * 100

    # %B: posizione del prezzo nelle bande (0=lower, 0.5=middle, 1=upper)
    band_width    = (df["boll_ub"] - df["boll_lb"]).replace(0, np.nan)
    df["boll_pct_b"] = (df["close"] - df["boll_lb"]) / band_width

    # ── ATR (Wilder)
    prev_close    = df["close"].shift(1).fillna(df["close"])
    tr            = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs()
    ], axis=1).max(axis=1)
    df["atr"]     = _rma(tr, atr_period)

    # ATR% — normalizzato su prezzo: permette confronto cross-asset
    # Fondamentale per calcolare stop e target in modo uniforme nello screener
    df["atr_pct"] = df["atr"] / df["close"].replace(0, np.nan) * 100

    return df


# ──────────────────────────────────────────────────────────────────────────────
# TREND STRENGTH (ADX + Efficiency Ratio)
# ──────────────────────────────────────────────────────────────────────────────

def add_trend_strength(df: pd.DataFrame, adx_period: int = 14, er_period: int = 14) -> pd.DataFrame:
    df = df.copy()

    # ── ADX / DI+  / DI-
    up_move   = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm   = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm  = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    prev_close = df["close"].shift(1).fillna(df["close"])
    tr         = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs()
    ], axis=1).max(axis=1)

    atr14      = _rma(tr, adx_period)
    plus_di    = 100 * _rma(pd.Series(plus_dm,  index=df.index), adx_period) / atr14.replace(0, np.nan)
    minus_di   = 100 * _rma(pd.Series(minus_dm, index=df.index), adx_period) / atr14.replace(0, np.nan)
    dx         = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)

    df["plus_di"]  = plus_di
    df["minus_di"] = minus_di
    df["adx"]      = _rma(dx, adx_period)

    # ── Efficiency Ratio (Kaufman)
    # > 0.5 = trend efficiente, < 0.3 = rumore / ranging
    net    = (df["close"] - df["close"].shift(er_period)).abs()
    path   = df["close"].diff().abs().rolling(er_period, min_periods=1).sum()
    df["er"] = net / path.replace(0, np.nan)
    df["er"] = df["er"].clip(0, 1)

    return df


# ──────────────────────────────────────────────────────────────────────────────
# TREND DIRECTION (SuperTrend + Linear Regression)
# ──────────────────────────────────────────────────────────────────────────────

def add_trend_direction(df: pd.DataFrame,
                        st_period: int = 10,
                        st_multiplier: float = 3.0,
                        lr_period: int = 20) -> pd.DataFrame:
    df = df.copy()

    # ── SuperTrend
    hl2       = (df["high"] + df["low"]) / 2
    prev_c    = df["close"].shift(1).fillna(df["close"])
    tr_st     = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_c).abs(),
        (df["low"]  - prev_c).abs()
    ], axis=1).max(axis=1)
    atr_st    = _rma(tr_st, st_period)

    upper_raw = hl2 + st_multiplier * atr_st
    lower_raw = hl2 - st_multiplier * atr_st

    upper     = np.zeros(len(df))
    lower     = np.zeros(len(df))
    st_vals   = np.zeros(len(df))
    direction = np.zeros(len(df), dtype=int)
    closes    = df["close"].values
    ur        = upper_raw.values
    lr_       = lower_raw.values

    upper[0]     = ur[0]
    lower[0]     = lr_[0]
    direction[0] = 1
    st_vals[0]   = upper[0]

    for i in range(1, len(df)):
        upper[i] = ur[i] if ur[i] < upper[i-1] or closes[i-1] > upper[i-1] else upper[i-1]
        lower[i] = lr_[i] if lr_[i] > lower[i-1] or closes[i-1] < lower[i-1] else lower[i-1]

        if st_vals[i-1] == upper[i-1]:
            direction[i] = 1 if closes[i] <= upper[i] else -1
        else:
            direction[i] = -1 if closes[i] >= lower[i] else 1

        st_vals[i] = upper[i] if direction[i] == 1 else lower[i]

    df["supertrend"]           = st_vals
    df["supertrend_direction"] = direction

    # ── Linear Regression (fitted value, slope, R²)
    n   = lr_period
    idx = np.arange(n)
    lr_val   = np.full(len(df), np.nan)
    lr_slope = np.full(len(df), np.nan)
    lr_r2    = np.full(len(df), np.nan)

    closes_arr = df["close"].values
    for i in range(n - 1, len(df)):
        y     = closes_arr[i - n + 1 : i + 1]
        x_bar = (n - 1) / 2
        y_bar = y.mean()
        ss_xx = ((idx - x_bar) ** 2).sum()
        ss_xy = ((idx - x_bar) * (y - y_bar)).sum()
        if ss_xx == 0:
            continue
        slope     = ss_xy / ss_xx
        intercept = y_bar - slope * x_bar
        fitted    = intercept + slope * idx
        ss_res    = ((y - fitted) ** 2).sum()
        ss_tot    = ((y - y_bar) ** 2).sum()

        lr_val[i]   = fitted[-1]
        lr_slope[i] = slope
        lr_r2[i]    = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    df["linear_regression"]       = lr_val
    df["linear_regression_slope"] = lr_slope
    df["linear_regression_r2"]    = lr_r2

    return df


# ──────────────────────────────────────────────────────────────────────────────
# ICHIMOKU CLOUD
# ──────────────────────────────────────────────────────────────────────────────

def add_ichimoku(df: pd.DataFrame,
                 tenkan: int = 9,
                 kijun: int = 26,
                 senkou_b: int = 52,
                 displacement: int = 26) -> pd.DataFrame:
    df = df.copy()

    def midpoint(h_series, l_series, period):
        return (h_series.rolling(period, min_periods=1).max() +
                l_series.rolling(period, min_periods=1).min()) / 2

    df["ichimoku_tenkan_sen"]  = midpoint(df["high"], df["low"], tenkan)
    df["ichimoku_kijun_sen"]   = midpoint(df["high"], df["low"], kijun)

    span_a = (df["ichimoku_tenkan_sen"] + df["ichimoku_kijun_sen"]) / 2
    span_b = midpoint(df["high"], df["low"], senkou_b)

    # Senkou Span proiettato in avanti di displacement barre
    df["ichimoku_senkou_span_a"] = span_a.shift(displacement)
    df["ichimoku_senkou_span_b"] = span_b.shift(displacement)

    # Chikou Span: close spostata indietro di displacement barre (no lookahead)
    df["ichimoku_chikou_span"]   = df["close"].shift(-displacement)

    # Cloud bias: +1 sopra la nuvola, -1 sotto, 0 dentro
    cloud_top = df[["ichimoku_senkou_span_a", "ichimoku_senkou_span_b"]].max(axis=1)
    cloud_bot = df[["ichimoku_senkou_span_a", "ichimoku_senkou_span_b"]].min(axis=1)
    df["ichimoku_bias"] = np.where(df["close"] > cloud_top,  1,
                          np.where(df["close"] < cloud_bot, -1, 0))

    # TK Cross: segnale di momentum Ichimoku
    df["ichimoku_tk_cross_bull"] = (
        (df["ichimoku_tenkan_sen"] > df["ichimoku_kijun_sen"]) &
        (df["ichimoku_tenkan_sen"].shift(1) <= df["ichimoku_kijun_sen"].shift(1))
    )
    df["ichimoku_tk_cross_bear"] = (
        (df["ichimoku_tenkan_sen"] < df["ichimoku_kijun_sen"]) &
        (df["ichimoku_tenkan_sen"].shift(1) >= df["ichimoku_kijun_sen"].shift(1))
    )

    return df


# ──────────────────────────────────────────────────────────────────────────────
# VOLUME
# ──────────────────────────────────────────────────────────────────────────────

def add_volume_indicators(df: pd.DataFrame, mfi_period: int = 14) -> pd.DataFrame:
    df = df.copy()

    # ── Volume SMA e ratio
    df["volume_sma20"]  = _sma(df["volume"], 20)
    df["volume_ratio"]  = df["volume"] / df["volume_sma20"].replace(0, np.nan)

    # ── MFI (Money Flow Index)
    tp          = (df["high"] + df["low"] + df["close"]) / 3
    mf          = tp * df["volume"]
    positive_mf = mf.where(tp > tp.shift(1), 0)
    negative_mf = mf.where(tp < tp.shift(1), 0)
    pos_sum     = positive_mf.rolling(mfi_period, min_periods=1).sum()
    neg_sum     = negative_mf.rolling(mfi_period, min_periods=1).sum()
    mfr         = pos_sum / neg_sum.replace(0, np.nan)
    df["mfi"]   = 100 - (100 / (1 + mfr))

    return df


# ──────────────────────────────────────────────────────────────────────────────
# STRUCTURE (Donchian + livelli chiave)
# ──────────────────────────────────────────────────────────────────────────────

def add_structure_levels(df: pd.DataFrame,
                         donchian_period: int = 20) -> pd.DataFrame:
    df = df.copy()

    # ── Donchian Channel — livelli strutturali puri senza deviazione standard
    # Il breakout del Donchian è il segnale di struttura più pulito su daily
    df["donchian_high"] = df["high"].rolling(donchian_period, min_periods=1).max()
    df["donchian_low"]  = df["low"].rolling(donchian_period, min_periods=1).min()
    df["donchian_mid"]  = (df["donchian_high"] + df["donchian_low"]) / 2

    # Breakout signals (chiusura sopra/sotto il Donchian della barra PRECEDENTE)
    df["donchian_breakout_up"]   = df["close"] > df["donchian_high"].shift(1)
    df["donchian_breakout_down"] = df["close"] < df["donchian_low"].shift(1)

    return df


# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE PRINCIPALE
# ──────────────────────────────────────────────────────────────────────────────

def compute_all(df: pd.DataFrame,
                rsi_period: int = 14,
                tsi_long: int = 13,
                tsi_short: int = 7,
                macd_fast: int = 12,
                macd_slow: int = 26,
                macd_sig: int = 9,
                bb_period: int = 20,
                atr_period: int = 14,
                adx_period: int = 14,
                er_period: int = 14,
                st_period: int = 10,
                st_mult: float = 3.0,
                lr_period: int = 20,
                tenkan: int = 9,
                kijun: int = 26,
                senkou_b: int = 52,
                displacement: int = 26,
                mfi_period: int = 14,
                donchian_period: int = 20) -> pd.DataFrame:
    """
    Pipeline completa: calcola tutti gli indicatori in sequenza.

    Args:
        df: DataFrame OHLCV con colonne [open, high, low, close, volume]
            e DatetimeIndex.

    Returns:
        DataFrame con tutte le colonne indicatori aggiunte.
    """
    required = {"open", "high", "low", "close", "volume"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"Colonne mancanti: {missing}")

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    df = add_moving_averages(df)
    df = add_momentum(df, rsi_period, tsi_long, tsi_short, macd_fast, macd_slow, macd_sig)
    df = add_volatility(df, bb_period, atr_period)
    df = add_trend_strength(df, adx_period, er_period)
    df = add_trend_direction(df, st_period, st_mult, lr_period)
    df = add_ichimoku(df, tenkan, kijun, senkou_b, displacement)
    df = add_volume_indicators(df, mfi_period)
    df = add_structure_levels(df, donchian_period)

    return df


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Genera dati sintetici per test
    import random
    random.seed(42)
    n = 300
    dates  = pd.date_range("2023-01-01", periods=n, freq="B")
    close  = 100 + np.cumsum(np.random.randn(n) * 0.8)
    high   = close + np.abs(np.random.randn(n) * 0.5)
    low    = close - np.abs(np.random.randn(n) * 0.5)
    open_  = close + np.random.randn(n) * 0.3
    volume = np.random.randint(1_000_000, 10_000_000, n).astype(float)

    test_df = pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume
    }, index=dates)

    result = compute_all(test_df)
    print(f"✓ compute_all: {len(result.columns)} colonne su {len(result)} barre")
    print(f"  Colonne: {sorted(result.columns.tolist())}")
    print(f"  Ultima riga RSI={result['rsi'].iloc[-1]:.1f}  "
          f"ADX={result['adx'].iloc[-1]:.1f}  "
          f"ATR%={result['atr_pct'].iloc[-1]:.2f}%")
