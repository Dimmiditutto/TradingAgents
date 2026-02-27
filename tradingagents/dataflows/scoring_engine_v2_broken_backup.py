"""
scoring_engine_v2.py - Advanced Swing Trading Scoring System
Upgraded from swing_system with 5-component weighted architecture

Architettura:
  Componente 1: Structure (30%) — CHoCH/BOS + MTF confluenza
  Componente 2: Trend Strength (25%) — ADX + ER + SuperTrend + Linear Regression R²
  Componente 3: Momentum (25%) — RSI + TSI + MACD + MFI
  Componente 4: Volatility Setup (10%) — Bollinger Bands + %B positioning
  Componente 5: Volume Confirmation (10%) — Volume Ratio + MFI confirmation

Score finale: 0-100 (media pesata dei 5 sub-score)
Entry: Score >= threshold (default 70) AND tutti i filtri obbligatori passano
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import numpy as np
import pandas as pd


# ==================== DATACLASSES ====================

@dataclass
class SwingSignalV2:
    """Segnale di swing trading con score dettagliato."""
    ticker: str
    timestamp: pd.Timestamp
    direction: str            # "LONG" o "SHORT"
    
    # Score principale
    score: float              # 0-100
    sub_scores: Dict[str, float] = field(default_factory=dict)  # structure, trend, momentum, volatility, volume
    
    # Filtri
    filters_passed: bool = True
    filter_failures: List[str] = field(default_factory=list)
    
    # Prezzi operativi
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target1: float = 0.0
    target2: float = 0.0
    atr: float = 0.0
    atr_pct: float = 0.0
    risk_reward: float = 0.0
    
    # Contesto tecnico
    weekly_trend: str = "UNDEFINED"
    daily_trend: str = "UNDEFINED"
    structure_event: str = ""
    adx: float = 0.0
    rsi: float = 0.0
    volume_ratio: float = 0.0
    pct_from_200sma: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "timestamp": str(self.timestamp),
            "direction": self.direction,
            "score": round(self.score, 1),
            "sub_scores": {k: round(v, 1) for k, v in self.sub_scores.items()},
            "filters_passed": self.filters_passed,
            "filter_failures": self.filter_failures,
            "entry_price": round(self.entry_price, 2),
            "stop_loss": round(self.stop_loss, 2),
            "target1": round(self.target1, 2),
            "target2": round(self.target2, 2),
            "atr": round(self.atr, 2),
            "atr_pct": round(self.atr_pct, 2),
            "risk_reward": round(self.risk_reward, 2),
            "weekly_trend": self.weekly_trend,
            "daily_trend": self.daily_trend,
            "structure_event": self.structure_event,
            "adx": round(self.adx, 1),
            "rsi": round(self.rsi, 1),
            "volume_ratio": round(self.volume_ratio, 2),
            "pct_from_200sma": round(self.pct_from_200sma, 2),
        }


# ==================== DEFAULT CONFIGURATION ====================

DEFAULT_WEIGHTS = {
    "structure": 0.30,
    "trend": 0.25,
    "momentum": 0.25,
    "volatility": 0.10,
    "volume": 0.10,
}

DEFAULT_FILTERS = {
    "require_weekly_uptrend": True,
    "require_above_200sma": True,
    "require_adx_min": 20.0,
    "require_supertrend_bull": True,
    "max_pct_from_200sma": 25.0,
    "min_atr_pct": 0.5,
    "max_atr_pct": 8.0,
}

DEFAULT_TRADE = {
    "stop_atr_mult": 1.5,
    "target1_atr_mult": 2.0,
    "target2_atr_mult": 3.5,
}


# ==================== COMPONENT 1: STRUCTURE SCORING ====================

def score_structure(df: pd.DataFrame, 
                   mtf_data: Dict,
                   direction: str,
                   weights: Dict = None) -> Tuple[float, Dict]:
    """
    Score dalla struttura di mercato (CHoCH/BOS + MTF confluenza).
    
    Criteri:
      - Ultimo evento è CHoCH ed è nel trend 💎 (+35)
      - Ultimi 2 event sono BOS nella stessa direzione (+25)
      - Weekly supporta daily trend (+15)
      - MTF double BOS (+10)
    
    Returns:
        (score 0-100, dettagli)
    """
    score = 50.0  # Base
    details = {}
    
    daily_signals = mtf_data.get("daily", {}).get("signals", [])
    weekly_signals = mtf_data.get("weekly", {}).get("signals", [])
    mtf_confluenza = mtf_data.get("mtf", {})
    
    # CHoCH bullish recente
    if daily_signals:
        last = daily_signals[-1]
        is_bullish = last.get("is_bullish", False)
        is_choch = last.get("is_choch", False)
        
        if is_choch and is_bullish and direction == "LONG":
            score += 35
            details["choch_bullish"] = True
        elif is_choch and not is_bullish and direction == "SHORT":
            score += 35
            details["choch_bearish"] = True
    
    # BOS confluenza
    if len(daily_signals) >= 2:
        recent_events = [s.get("event", "") for s in daily_signals[-2:]]
        if all("BOS_UP" in e for e in recent_events) and direction == "LONG":
            score += 25
            details["double_bos_up"] = True
    
    # Weekly support
    weekly_trend = mtf_data.get("weekly", {}).get("trend", "UNDEFINED")
    if weekly_trend == "UPTREND" and direction == "LONG":
        score += 15
        details["weekly_uptrend"] = True
    elif weekly_trend == "DOWNTREND" and direction == "SHORT":
        score += 15
        details["weekly_downtrend"] = True
    
    # MTF confluenza
    if mtf_confluenza.get("double_bos"):
        score += 10
        details["mtf_double_bos"] = True
    
    return min(100.0, score), details


# ==================== COMPONENT 2: TREND STRENGTH ====================

def score_trend_strength(df: pd.DataFrame, direction: str) -> Tuple[float, Dict]:
    """
    Score dalla forza del trend (ADX + ER + SuperTrend + LR R²).
    
    Criteri:
      - ADX >= 35: strong trend (+25)
      - ADX 20-35: moderate trend (+15)
      - Efficiency Ratio >= 0.5 (+15)
      - SuperTrend bullish per LONG (+20)
      - Linear Regression R² >= 0.7 (+15)
    
    Returns:
        (score 0-100, dettagli)
    """
    score = 0.0
    details = {}
    
    # ADX
    adx = df["adx"].iloc[-1] if "adx" in df.columns else 0.0
    
    if adx >= 35:
        score += 25
        details["adx_strong"] = adx
    elif adx >= 20:
        score += 15
        details["adx_moderate"] = adx
    
    # Efficiency Ratio (approx da Close momentum)
    close_change = abs(df["close"].iloc[-1] - df["close"].iloc[-20])
    close_range = sum(abs(df["close"].iloc[-i] - df["close"].iloc[-i-1]) for i in range(1, 20))
    er = close_change / (close_range + 0.001) if close_range > 0 else 0.0
    
    if er >= 0.5:
        score += 15
        details["efficiency_ratio_high"] = er
    
    # SuperTrend (approssimativo dai dati)
    supertrend_bull = False
    if "supertrend" in df.columns:
        supertrend_bull = df["close"].iloc[-1] > df["supertrend"].iloc[-1]
    
    if supertrend_bull and direction == "LONG":
        score += 20
        details["supertrend_bullish"] = True
    
    # Linear Regression R²
    if "linreg_r2" in df.columns:
        r2 = df["linreg_r2"].iloc[-1]
        if r2 >= 0.7:
            score += 15
            details["linreg_r2_high"] = r2
    
    return min(100.0, score), details


# ==================== COMPONENT 3: MOMENTUM ====================

def score_momentum(df: pd.DataFrame, direction: str) -> Tuple[float, Dict]:
    """
    Score da momentum (RSI + TSI + MACD + MFI).
    
    Criteri:
      - RSI 40-50 per entry LONG (non overextended) (+15)
      - TSI > 0 e crossing up (+15)
      - MACD histogram positivo e crescente (+20)
      - MFI > 50 e crescente (+10)
    
    Returns:
        (score 0-100, dettagli)
    """
    score = 0.0
    details = {}
    
    # RSI
    rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50.0
    if 40 <= rsi <= 60:
        score += 15
        details["rsi_neutral"] = rsi
    elif rsi > 70 and direction == "SHORT":
        score += 10
        details["rsi_overbought"] = rsi
    elif rsi < 30 and direction == "LONG":
        score += 10
        details["rsi_oversold"] = rsi
    
    # TSI (True Strength Index)
    if "tsi" in df.columns:
        tsi = df["tsi"].iloc[-1]
        tsi_prev = df["tsi"].iloc[-2] if len(df) > 1 else tsi
        if tsi > 0 and tsi_prev <= 0 and direction == "LONG":
            score += 15
            details["tsi_crossover_bullish"] = tsi
    
    # MACD Histogram
    if "macd_hist" in df.columns:
        macd_h = df["macd_hist"].iloc[-1]
        macd_h_prev = df["macd_hist"].iloc[-2] if len(df) > 1 else macd_h
        
        if macd_h > 0 and macd_h > macd_h_prev:
            score += 20
            details["macd_hist_growing"] = macd_h
    
    # MFI (Money Flow Index)
    if "mfi" in df.columns:
        mfi = df["mfi"].iloc[-1]
        mfi_prev = df["mfi"].iloc[-2] if len(df) > 1 else mfi
        
        if mfi > 50 and mfi > mfi_prev:
            score += 10
            details["mfi_strong"] = mfi
    
    return min(100.0, score), details


# ==================== COMPONENT 4: VOLATILITY SETUP ====================

def score_volatility(df: pd.DataFrame) -> Tuple[float, Dict]:
    """
    Score dalla configurazione della volatilità (Bollinger Bands + %B).
    
    Criteri:
      - %B tra 0.2 e 0.8 (non agli estremi) (+30)
      - Bandwidth crescente (volatilità espandente) (+20)
      - Price near midline (+15)
    
    Returns:
        (score 0-100, dettagli)
    """
    score = 0.0
    details = {}
    
    if "boll_pct" not in df.columns or "boll_bandwidth" not in df.columns:
        return 30.0, {}
    
    pct_b = df["boll_pct"].iloc[-1]
    bandwidth = df["boll_bandwidth"].iloc[-1]
    bandwidth_prev = df["boll_bandwidth"].iloc[-2] if len(df) > 1 else bandwidth
    
    # %B positioning
    if 0.2 <= pct_b <= 0.8:
        score += 30
        details["pct_b_neutral"] = pct_b
    elif 0.3 <= pct_b <= 0.7:
        score += 15
        details["pct_b_mid"] = pct_b
    
    # Bandwidth expansion
    if bandwidth > bandwidth_prev:
        score += 20
        details["bandwidth_expanding"] = bandwidth
    
    # Price vicino midline
    if 0.4 <= pct_b <= 0.6:
        score += 15
        details["price_near_midline"] = pct_b
    
    return min(100.0, score), details


# ==================== COMPONENT 5: VOLUME CONFIRMATION ====================

def score_volume(df: pd.DataFrame, direction: str) -> Tuple[float, Dict]:
    """
    Score da volume e confirmazione.
    
    Criteri:
      - Volume Ratio >= 1.3 (volume sopra media) (+25)
      - MFI e volume concordi (+20)
      - Volume crescente negli ultimi 3 bar (+15)
    
    Returns:
        (score 0-100, dettagli)
    """
    score = 0.0
    details = {}
    
    # Volume Ratio
    if "volume_ratio" in df.columns:
        vol_ratio = df["volume_ratio"].iloc[-1]
        if vol_ratio >= 1.3:
            score += 25
            details["high_volume_ratio"] = vol_ratio
        elif vol_ratio >= 1.0:
            score += 12
            details["above_avg_volume"] = vol_ratio
    
    # MFI e volume concordi
    if "mfi" in df.columns and "volume" in df.columns:
        mfi = df["mfi"].iloc[-1]
        vol = df["volume"].iloc[-1]
        vol_prev = df["volume"].iloc[-2] if len(df) > 1 else vol
        
        mfi_bullish = mfi > 50
        vol_up = vol > vol_prev
        
        if (mfi_bullish and vol_up and direction == "LONG") or \
           (not mfi_bullish and vol_up and direction == "SHORT"):
            score += 20
            details["mfi_volume_aligned"] = True
    
    # Volume trend
    if len(df) >= 3:
        vols = df["volume"].iloc[-3:].values
        if vols[-1] > vols[-2] > vols[-3]:
            score += 15
            details["volume_increasing"] = True
    
    return min(100.0, score), details


# ==================== MANDATORY FILTERS ====================

def check_filters(df: pd.DataFrame, 
                 mtf_data: Dict,
                 direction: str,
                 filters: Dict = None) -> Tuple[bool, List[str]]:
    """
    Verifica filtri obbligatori (bloccano il segnale se falliscono).
    
    Filtri:
      1. Weekly trend = UPTREND (per LONG)
      2. Close > SMA200
      3. ADX >= 20
      4. SuperTrend bullish (per LONG)
      5. ATR% tra 0.5% e 8%
      6. Non oltre +25% dalla SMA200
    
    Returns:
        (all_passed, lista dei fallimenti)
    """
    if filters is None:
        filters = DEFAULT_FILTERS
    
    failures = []
    
    # Filter 1: Weekly trend
    weekly_trend = mtf_data.get("weekly", {}).get("trend", "UNDEFINED")
    if filters.get("require_weekly_uptrend", True):
        if direction == "LONG" and weekly_trend != "UPTREND":
            failures.append(f"weekly_trend={weekly_trend} (need UPTREND for LONG)")
        elif direction == "SHORT" and weekly_trend != "DOWNTREND":
            failures.append(f"weekly_trend={weekly_trend} (need DOWNTREND for SHORT)")
    
    # Filter 2: Close > SMA200
    if filters.get("require_above_200sma", True):
        sma200 = df["close_200_sma"].iloc[-1] if "close_200_sma" in df.columns else df["close"].iloc[-1]
        if df["close"].iloc[-1] <= sma200 and direction == "LONG":
            failures.append(f"close <= SMA200 ({df['close'].iloc[-1]:.2f} <= {sma200:.2f})")
    
    # Filter 3: ADX >= 20
    adx_min = filters.get("require_adx_min", 20.0)
    adx = df["adx"].iloc[-1] if "adx" in df.columns else 0.0
    if adx < adx_min:
        failures.append(f"ADX={adx:.1f} < {adx_min}")
    
    # Filter 4: SuperTrend bullish
    if filters.get("require_supertrend_bull", True):
        if "supertrend" in df.columns:
            is_bullish = df["close"].iloc[-1] > df["supertrend"].iloc[-1]
            if is_bullish and direction != "LONG":
                failures.append("SuperTrend bullish but LONG expected")
            elif not is_bullish and direction == "LONG":
                failures.append("SuperTrend not bullish for LONG")
    
    # Filter 5: ATR%
    atr_pct = df["atr_pct"].iloc[-1] if "atr_pct" in df.columns else 1.0
    min_atr = filters.get("min_atr_pct", 0.5)
    max_atr = filters.get("max_atr_pct", 8.0)
    
    if not (min_atr <= atr_pct <= max_atr):
        failures.append(f"ATR%={atr_pct:.2f} outside [{min_atr}, {max_atr}]")
    
    # Filter 6: Not too far from SMA200
    max_pct = filters.get("max_pct_from_200sma", 25.0)
    if "pct_from_200sma" in df.columns:
        pct_from = df["pct_from_200sma"].iloc[-1]
        if direction == "LONG" and pct_from > max_pct:
            failures.append(f"pct_from_200sma={pct_from:.1f}% > {max_pct}% (too extended)")
    
    return len(failures) == 0, failures


# ==================== PRICE LEVELS ====================

def calculate_levels(df: pd.DataFrame,
                    direction: str,
                    atr: float,
                    trade_params: Dict = None) -> Tuple[float, float, float]:
    """
    Calcola entry, stop loss, target basati su ATR.
    
    Returns:
        (entry_price, stop_loss, target)
    """
    if trade_params is None:
        trade_params = DEFAULT_TRADE
    
    entry = df["close"].iloc[-1]
    
    stop_mult = trade_params.get("stop_atr_mult", 1.5)
    target_mult = trade_params.get("target1_atr_mult", 2.0)
    
    if direction == "LONG":
        stop = entry - stop_mult * atr
        target = entry + target_mult * atr
    else:  # SHORT
        stop = entry + stop_mult * atr
        target = entry - target_mult * atr
    
    return entry, stop, target


# ==================== MAIN SCORING FUNCTION ====================

def score_signal(ticker: str,
                df: pd.DataFrame,
                mtf_data: Dict,
                direction: str,
                weights: Dict = None,
                filters: Dict = None,
                trade_params: Dict = None,
                min_score: float = 70.0) -> Optional[SwingSignalV2]:
    """
    Calcola lo score completo per un segnale swing.
    
    Args:
        ticker: simbolo
        df: DataFrame giornaliero con indicatori
        mtf_data: dati multi-timeframe da market_structure_choch
        direction: "LONG" o "SHORT"
        weights: pesi componenti (default: DEFAULT_WEIGHTS)
        filters: filtri obbligatori (default: DEFAULT_FILTERS)
        trade_params: parametri trade/stop/target (default: DEFAULT_TRADE)
        min_score: score minimo per entry (default: 70.0)
    
    Returns:
        SwingSignalV2 se filters passano e score >= min_score, altrimenti None
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    if filters is None:
        filters = DEFAULT_FILTERS
    if trade_params is None:
        trade_params = DEFAULT_TRADE
    
    # Check filtri
    filters_passed, failures = check_filters(df, mtf_data, direction, filters)
       # Default MTF data se non fornito
       if mtf_data is None:
           mtf_data = {}
       
   
   # Calcola sub-score
   structure_score, structure_details = score_structure(df, mtf_data, direction)
   trend_score, trend_details = score_trend_strength(df, direction)
   momentum_score, momentum_details = score_momentum(df, direction)
   volatility_score, volatility_details = score_volatility(df)
   volume_score, volume_details = score_volume(df, direction)
    
    # Calcola sub-score
    structure_score, structure_details = score_structure(df, mtf_data, direction)
    trend_score, trend_details = score_trend_strength(df, direction)
    momentum_score, momentum_details = score_momentum(df, direction)
    volatility_score, volatility_details = score_volatility(df)
    volume_score, volume_details = score_volume(df, direction)
    
    # Score finale
    score = (
        structure_score * weights.get("structure", 0.30) +
        trend_score * weights.get("trend", 0.25) +
        momentum_score * weights.get("momentum", 0.25) +
        volatility_score * weights.get("volatility", 0.10) +
        volume_score * weights.get("volume", 0.10)
    )
    
    # ATR e livelli
    atr = df["atr"].iloc[-1] if "atr" in df.columns else 1.0
    atr_pct = df["atr_pct"].iloc[-1] if "atr_pct" in df.columns else 1.0
    entry, stop, target = calculate_levels(df, direction, atr, trade_params)
    risk_reward = abs(target - entry) / (abs(entry - stop) + 0.0001)
    
    # Se filtri falliscono, ritorna None
    if not filters_passed:
        return None
    
    # Se score sotto soglia, ritorna None
    if score < min_score:
        return None
    
    # Crea segnale
    signal = SwingSignalV2(
        ticker=ticker,
        timestamp=df.index[-1],
        direction=direction,
        score=score,
        sub_scores={
            "structure": structure_score,
            "trend": trend_score,
            "momentum": momentum_score,
            "volatility": volatility_score,
            "volume": volume_score,
        },
        filters_passed=True,
        entry_price=entry,
        stop_loss=stop,
        target1=target,
        atr=atr,
        atr_pct=atr_pct,
        risk_reward=risk_reward,
        weekly_trend=mtf_data.get("weekly", {}).get("trend", "UNDEFINED"),
        daily_trend=mtf_data.get("daily", {}).get("trend", "UNDEFINED"),
        structure_event=mtf_data.get("daily", {}).get("signals", [{}])[-1].get("event", ""),
        adx=df["adx"].iloc[-1] if "adx" in df.columns else 0.0,
        rsi=df["rsi"].iloc[-1] if "rsi" in df.columns else 50.0,
        volume_ratio=df["volume_ratio"].iloc[-1] if "volume_ratio" in df.columns else 1.0,
        pct_from_200sma=df["pct_from_200sma"].iloc[-1] if "pct_from_200sma" in df.columns else 0.0,
    )
    
    return signal


def score_both_directions(ticker: str,
                         df: pd.DataFrame,
                         mtf_data: Dict,
                         weights: Dict = None,
                         filters: Dict = None,
                         trade_params: Dict = None,
                         min_score: float = 70.0) -> List[SwingSignalV2]:
    """
    Testa entrambe le direzioni e ritorna i segnali validi.
    """
    results = []
    
    for direction in ["LONG", "SHORT"]:
        signal = score_signal(
            ticker, df, mtf_data, direction,
            weights, filters, trade_params, min_score
        )
        if signal:
            results.append(signal)
    
    return results
