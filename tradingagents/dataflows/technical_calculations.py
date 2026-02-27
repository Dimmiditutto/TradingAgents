"""
Technical Indicators Calculation Module
Calcola indicatori tecnici localmente da dati OHLCV, eliminando necessità di API calls.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average"""
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(
    prices: pd.Series, 
    fast: int = 12, 
    slow: int = 26, 
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD, Signal Line, and Histogram"""
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    prices: pd.Series, 
    period: int = 20, 
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands (Upper, Middle, Lower)"""
    middle = calculate_sma(prices, period)
    std = prices.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return upper, middle, lower


def calculate_atr(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    period: int = 14
) -> pd.Series:
    """Average True Range"""
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def calculate_vwma(
    prices: pd.Series, 
    volume: pd.Series, 
    period: int = 20
) -> pd.Series:
    """Volume Weighted Moving Average"""
    return (prices * volume).rolling(window=period).sum() / volume.rolling(window=period).sum()


# ==================== NUOVI INDICATORI PER SWING TRADING ====================

def calculate_adx(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    period: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Average Directional Index (ADX) - Forza del Trend
    Returns: (ADX, +DI, -DI)
    
    ADX > 25: Trend forte
    ADX < 20: Trend debole/laterale
    """
    # True Range
    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift()).abs(),
        'lc': (low - close.shift()).abs()
    }).max(axis=1)
    
    # Directional Movement
    up_move = high - high.shift()
    down_move = low.shift() - low
    
    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)
    
    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move
    
    # Smoothed indicators
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # ADX calculation
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di


def calculate_efficiency_ratio(prices: pd.Series, period: int = 10) -> pd.Series:
    """
    Efficiency Ratio (ER) - Forza del Trend
    Kaufman's Adaptive Moving Average component
    
    ER vicino a 1: Trend forte e direzionale
    ER vicino a 0: Mercato laterale/noise
    """
    change = (prices - prices.shift(period)).abs()
    volatility = (prices.diff().abs()).rolling(window=period).sum()
    
    er = change / volatility
    er = er.fillna(0)  # Handle division by zero
    
    return er


def calculate_supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0
) -> Tuple[pd.Series, pd.Series]:
    """
    SuperTrend Indicator - Direzione del Trend
    Returns: (supertrend_values, trend_direction)
    
    trend_direction: 1 = uptrend, -1 = downtrend
    """
    atr = calculate_atr(high, low, close, period)
    hl_avg = (high + low) / 2
    
    # Basic bands
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)
    
    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1
    
    for i in range(1, len(close)):
        # Uptrend
        if close.iloc[i] > supertrend.iloc[i-1]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        # Downtrend
        elif close.iloc[i] < supertrend.iloc[i-1]:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1
        # Continuation
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            direction.iloc[i] = direction.iloc[i-1]
            
            if direction.iloc[i] == 1 and lower_band.iloc[i] < supertrend.iloc[i-1]:
                supertrend.iloc[i] = lower_band.iloc[i]
            elif direction.iloc[i] == -1 and upper_band.iloc[i] > supertrend.iloc[i-1]:
                supertrend.iloc[i] = upper_band.iloc[i]
    
    return supertrend, direction


def calculate_linear_regression(
    prices: pd.Series,
    period: int = 20
) -> Tuple[pd.Series, pd.Series, float]:
    """
    Linear Regression - Direzione del Trend
    Returns: (regression_line, regression_slope, r_squared)
    
    For swing trading:
    - period=20: captures ~1 month trend (standard)
    - period=10: captures ~2 week trend (more reactive for short-term swings)
    
    slope > 0: Uptrend
    slope < 0: Downtrend
    r_squared vicino a 1: Trend forte e lineare (>0.6 per swing valida)
    """
    regression_line = pd.Series(index=prices.index, dtype=float)
    regression_slope = pd.Series(index=prices.index, dtype=float)
    
    for i in range(period - 1, len(prices)):
        y = prices.iloc[i - period + 1:i + 1].values
        x = np.arange(len(y))
        
        # Linear regression: y = mx + b
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        intercept = coeffs[1]
        
        # Predicted value for current point
        regression_line.iloc[i] = slope * (period - 1) + intercept
        regression_slope.iloc[i] = slope
    
    # Calculate R-squared for the last period
    if len(prices) >= period:
        y = prices.iloc[-period:].values
        x = np.arange(len(y))
        coeffs = np.polyfit(x, y, 1)
        y_pred = np.polyval(coeffs, x)
        
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    else:
        r_squared = 0
    
    return regression_line, regression_slope, r_squared


def calculate_ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52
) -> Dict[str, pd.Series]:
    """
    Ichimoku Cloud - Direzione e Forza del Trend
    
    Returns dict with:
    - tenkan_sen (Conversion Line)
    - kijun_sen (Base Line)
    - senkou_span_a (Leading Span A)
    - senkou_span_b (Leading Span B)
    - chikou_span (Lagging Span)
    
    Prezzo sopra la cloud: Uptrend
    Prezzo sotto la cloud: Downtrend
    """
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
    tenkan_sen = (
        high.rolling(window=tenkan_period).max() + 
        low.rolling(window=tenkan_period).min()
    ) / 2
    
    # Kijun-sen (Base Line): (26-period high + 26-period low)/2
    kijun_sen = (
        high.rolling(window=kijun_period).max() + 
        low.rolling(window=kijun_period).min()
    ) / 2
    
    # Senkou Span A (Leading Span A): (Conversion Line + Base Line)/2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun_period)
    
    # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
    senkou_span_b = (
        (high.rolling(window=senkou_b_period).max() + 
         low.rolling(window=senkou_b_period).min()) / 2
    ).shift(kijun_period)
    
    # Chikou Span (Lagging Span): Close shifted back 26 periods
    chikou_span = close.shift(-kijun_period)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span,
    }


def calculate_tsi(
    prices: pd.Series,
    long_period: int = 13,
    short_period: int = 7,
    signal_period: int = 7
) -> Tuple[pd.Series, pd.Series]:
    """
    True Strength Index (TSI) - Momentum
    Default params optimized for swing trading (13/7) instead of (25/13) for higher reactivity
    Returns: (TSI, Signal Line)
    
    TSI > 0: Bullish momentum
    TSI < 0: Bearish momentum
    TSI crossover Signal: Buy/Sell signals
    
    Swing Trading Note: (13/7) gives 2-3 bar lead vs RSI, smoother than RSI without whipsaws
    """
    # Price momentum
    momentum = prices.diff()
    
    # Double smoothed momentum
    momentum_ema_long = momentum.ewm(span=long_period, adjust=False).mean()
    momentum_ema_short = momentum_ema_long.ewm(span=short_period, adjust=False).mean()
    
    # Double smoothed absolute momentum
    abs_momentum = momentum.abs()
    abs_momentum_ema_long = abs_momentum.ewm(span=long_period, adjust=False).mean()
    abs_momentum_ema_short = abs_momentum_ema_long.ewm(span=short_period, adjust=False).mean()
    
    # TSI calculation
    tsi = 100 * (momentum_ema_short / abs_momentum_ema_short)
    
    # Signal line
    signal = tsi.ewm(span=signal_period, adjust=False).mean()
    
    return tsi, signal


# ==================== NUOVE METRICHE SWING TRADING ====================

def calculate_bollinger_bandwidth(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> pd.Series:
    """
    Bollinger Bandwidth - Volatility Compression Metric
    Misura la "larghezza" delle Bollinger Bands normalizzata
    
    Formula: (boll_ub - boll_lb) / boll_middle * 100
    
    Utilizzo swing:
    - Bandwidth < 10: Estrema compressione, breakout imminente
    - Bandwidth > 30: Volatilità elevata, rischio di mean reversion
    - Rising bandwidth: Volatilità in aumento (buono per breakout)
    - Falling bandwidth: Compressione (setup imminente)
    
    Fondamentale per identificare i periodi di setup pre-breakout
    """
    upper, middle, lower = calculate_bollinger_bands(prices, period, std_dev)
    
    bandwidth = ((upper - lower) / middle) * 100
    bandwidth = bandwidth.fillna(0)
    
    return bandwidth


def calculate_volume_ratio(
    volume: pd.Series,
    period: int = 20
) -> pd.Series:
    """
    Volume Ratio - Forza del segnale basata su volume
    Ratio = volume corrente / SMA(volume, 20)
    
    Utilizzo:
    - Volume Ratio > 1.5: Breakout con volume FORTE (alto follow-through)
    - Volume Ratio 1.0-1.5: Breakout standard
    - Volume Ratio < 0.7: Breakout DEBOLE (bassa affidabilità)
    
    Critico per qualificare i breakout strutturali su swing.
    Storicamente: BOS con VR > 1.5 ha win rate 20-30% superiore.
    """
    volume_sma = volume.rolling(window=period).mean()
    volume_ratio = volume / volume_sma
    volume_ratio = volume_ratio.fillna(0)
    
    return volume_ratio


def calculate_donchian_channel(
    high: pd.Series,
    low: pd.Series,
    period: int = 20
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Donchian Channel - Struttura di supporto/resistenza basata su prezzi effettivi
    Returns: (high_channel, low_channel, midline)
    
    Diverso da Bollinger: usa max/min effettivi, non deviazione standard
    
    Utilizzo swing:
    - Breakout sopra Donchian High: BOS rialzista
    - Breakdown sotto Donchian Low: BOS ribassista
    - Oscillazione tra canale: range-bound, wait for breakout
    
    Vantaggi rispetto Bollinger:
    - Meno falsi segnali in mercati molto volatili
    - Rispecchia struttura effettiva vs teorica
    - Setup di breakout più puri
    """
    donchian_high = high.rolling(window=period).max()
    donchian_low = low.rolling(window=period).min()
    donchian_mid = (donchian_high + donchian_low) / 2
    
    return donchian_high, donchian_low, donchian_mid


def calculate_percent_from_200sma(
    close: pd.Series,
    close_200_sma: pd.Series
) -> pd.Series:
    """
    Percentuale dalla 200 SMA - Screening per mean reversion
    Misura: (close - close_200_sma) / close_200_sma * 100
    
    Valori:
    - > +20%:  Vastly overbought, mean reversion risk HIGH
    - 0 to +20%: Uptrend normale, buy setup possibile
    - -20% to 0: Downtrend normale, sell setup possibile
    - < -20%: Vastly oversold, extreme accumulation potential
    
    Per swing trading:
    - Filtra titoli dove il setup ha statistically basso win rate
    - > +25%: Probabilità di ritracciamento >70% nei 10gg successivi
    - < -25%: Probabilità di rimbalzo >70% nei 10gg successivi
    
    Essenziale per screening: scarta candidati in territory estremo
    """
    percent_from_200 = ((close - close_200_sma) / close_200_sma) * 100
    percent_from_200 = percent_from_200.fillna(0)
    
    return percent_from_200


def calculate_atr_percent(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    ATR Percentage - Volatilità normalizzata per comparazione cross-asset
    Formula: (ATR / close) * 100
    
    Utilizzo essenziale:
    - ATR assoluto PER è non-comparabile: NVDA a 800$ vs titolo a 20$
    - ATR% normalizza: puoi confrontare volatilità uniformemente
    - Consente calcolo uniforme di target/stop in screening
    
    Interpretazione:
    - ATR% > 3%: Titolo volatile, position size ridotta
    - ATR% 1-3%: Volatilità normale (target 0,5-1.5x ATR%)
    - ATR% < 1%: Titolo stabile, position size aumentata
    
    Fondamentale per:
    - Sizing coerente tra titoli a prezzi diversi
    - Calcolo stop loss uniforme (1.5x ATR% per tutti)
    - Calcolo target uniforme (3x ATR% = ~2-5% su daily)
    """
    atr = calculate_atr(high, low, close, period)
    atr_percent = (atr / close) * 100
    atr_percent = atr_percent.fillna(0)
    
    return atr_percent


# ==================== FUNZIONE MASTER ====================

def get_all_indicators(df: pd.DataFrame, swing_mode: bool = True) -> Dict[str, any]:
    """
    Calcola tutti gli indicatori tecnici da un DataFrame OHLCV
    
    Args:
        df: DataFrame con colonne ['open', 'high', 'low', 'close', 'volume']
        swing_mode: True per swing trading (include tutti gli indicatori avanzati)
    
    Returns:
        Dictionary con tutti gli indicatori calcolati
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
        raise ValueError("DataFrame must contain 'open', 'high', 'low', 'close' columns")
    
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df.get('volume', pd.Series([0] * len(df)))
    
    indicators = {}
    
    # Indicatori base (sempre calcolati)
    indicators['close_10_ema'] = calculate_ema(close, 10)
    indicators['close_50_sma'] = calculate_sma(close, 50)
    indicators['close_200_sma'] = calculate_sma(close, 200)
    
    indicators['rsi'] = calculate_rsi(close, 14)
    
    macd, macds, macdh = calculate_macd(close)
    indicators['macd'] = macd
    indicators['macds'] = macds
    indicators['macdh'] = macdh
    
    boll_ub, boll, boll_lb = calculate_bollinger_bands(close)
    indicators['boll_ub'] = boll_ub
    indicators['boll'] = boll
    indicators['boll_lb'] = boll_lb
    
    indicators['atr'] = calculate_atr(high, low, close)
    
    if len(volume) > 0 and volume.sum() > 0:
        indicators['vwma'] = calculate_vwma(close, volume, 20)
    
    # Indicatori avanzati per SWING TRADING
    if swing_mode:
        # Forza del trend
        adx, plus_di, minus_di = calculate_adx(high, low, close, 14)
        indicators['adx'] = adx
        indicators['plus_di'] = plus_di
        indicators['minus_di'] = minus_di
        indicators['er'] = calculate_efficiency_ratio(close, 10)
        
        # Direzione del trend
        supertrend, st_direction = calculate_supertrend(high, low, close, 10, 3.0)
        indicators['supertrend'] = supertrend
        indicators['supertrend_direction'] = st_direction
        
        linreg, linreg_slope, r_squared = calculate_linear_regression(close, 20)
        indicators['linear_regression'] = linreg
        indicators['linear_regression_slope'] = linreg_slope
        indicators['linear_regression_r2'] = r_squared
        
        ichimoku = calculate_ichimoku(high, low, close)
        indicators.update({f'ichimoku_{k}': v for k, v in ichimoku.items()})
        
        # Momentum
        tsi, tsi_signal = calculate_tsi(close)  # Default: 13/7 for swing reactivity
        indicators['tsi'] = tsi
        indicators['tsi_signal'] = tsi_signal
        
        # Linear Regression - Dual periods: 20 (standard) and 10 (short-term reactive)
        linreg_20, linreg_slope_20, r2_20 = calculate_linear_regression(close, 20)
        linreg_10, linreg_slope_10, r2_10 = calculate_linear_regression(close, 10)
        indicators['linear_regression_20'] = linreg_20
        indicators['linear_regression_slope_20'] = linreg_slope_20
        indicators['linear_regression_20_r2'] = r2_20
        indicators['linear_regression_10'] = linreg_10
        indicators['linear_regression_slope_10'] = linreg_slope_10
        indicators['linear_regression_10_r2'] = r2_10
        
        # NEW: Bollinger Bandwidth - Volatility compression metric
        indicators['bollinger_bandwidth'] = calculate_bollinger_bandwidth(close, 20, 2.0)
        
        # NEW: Volume Ratio - Breakout strength qualification
        if len(volume) > 0 and volume.sum() > 0:
            indicators['volume_ratio'] = calculate_volume_ratio(volume, 20)
        
        # NEW: Donchian Channel - Price-based structure
        donchian_h, donchian_l, donchian_mid = calculate_donchian_channel(high, low, 20)
        indicators['donchian_high'] = donchian_h
        indicators['donchian_low'] = donchian_l
        indicators['donchian_mid'] = donchian_mid
        
        # NEW: Percent from 200 SMA - Mean reversion screening
        indicators['percent_from_200sma'] = calculate_percent_from_200sma(close, indicators['close_200_sma'])
        
        # NEW: ATR Percent - Cross-asset comparable volatility
        indicators['atr_percent'] = calculate_atr_percent(high, low, close, 14)
    
    return indicators


def format_indicators_for_display(indicators: Dict[str, any], decimals: int = 2) -> Dict[str, float]:
    """
    Formatta gli indicatori per display (ultimo valore)
    
    Returns:
        Dictionary con l'ultimo valore di ogni indicatore
    """
    formatted = {}
    
    for key, value in indicators.items():
        if isinstance(value, pd.Series):
            last_value = value.iloc[-1]
            if pd.notna(last_value):
                formatted[key] = round(last_value, decimals)
            else:
                formatted[key] = None
        else:
            # Per valori singoli come r_squared
            formatted[key] = round(value, decimals) if value is not None else None
    
    return formatted
