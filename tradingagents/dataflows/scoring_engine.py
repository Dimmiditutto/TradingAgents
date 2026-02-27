"""
Signal Scoring Engine - Unified 0-100 Score for Trade Setup Quality

Architecture:
  Combines:
    ✓ Multi-Timeframe confluence (weekly + daily)
    ✓ 44+ technical indicators
    ✓ Structure analysis (pivots, ChoCH, BOS)
    ✓ Risk metrics (ATR%, % from 200 SMA)
  
  Output: Single 0-100 score per symbol per direction (LONG/SHORT)
"""

import pandas as pd
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum

from .technical_calculations import get_all_indicators
from .multi_timeframe import MultiTimeframeData
from .structure_detector import SwingClassifier


class TradeDirection(Enum):
    LONG = 1
    SHORT = -1


@dataclass
class SignalScore:
    """Container for signal scoring result"""
    symbol: str
    direction: TradeDirection
    total_score: float  # 0-100
    
    # Component scores (each 0-100)
    trend_strength: float       # ADX, ER, supertrend
    direction_confluence: float # Multi-TF alignment
    volume_quality: float       # Volume ratio, VWMA
    structure_quality: float    # ChoCH, BOS, key levels
    risk_profile: float         # ATR%, % from 200 SMA, extremes
    
    # Break-even components
    adx_value: float
    volume_ratio: float
    pct_from_200sma: float
    atr_pct: float
    weekly_trend: int
    
    # Reasoning
    strengths: List[str]  # What's good
    weaknesses: List[str] # What's concerning
    
    def to_dict(self) -> Dict:
        """Export as dictionary"""
        return {
            'symbol': self.symbol,
            'direction': self.direction.name,
            'total_score': round(self.total_score, 1),
            'trend_strength': round(self.trend_strength, 1),
            'direction_confluence': round(self.direction_confluence, 1),
            'volume_quality': round(self.volume_quality, 1),
            'structure_quality': round(self.structure_quality, 1),
            'risk_profile': round(self.risk_profile, 1),
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
        }


class ScoringEngine:
    """Generate unified 0-100 signal score"""
    
    def __init__(self):
        self.classifier = SwingClassifier()
    
    def score_mtf_signal(self, mtf: MultiTimeframeData) -> Tuple[SignalScore, SignalScore]:
        """
        Score both LONG and SHORT signals for symbol
        
        Returns:
            (long_score, short_score) - SignalScore for each direction
        
        Methodology:
          Each component 0-100:
            - Trend Strength: ADX (>25=60, >35=80, >45=100)
            - Direction Confluence: Weekly + Daily alignment
            - Volume Quality: VR (>1.5=80, >2.0=100)
            - Structure Quality: ChoCH/BOS detected, key levels intact
            - Risk Profile: ATR%, extremes, mean reversion
          
          Total = weighted average of components
            30% Trend Strength
            25% Direction Confluence
            20% Volume Quality
            15% Structure Quality
            10% Risk Profile
        """
        
        # Extract key indicators
        daily = mtf.daily.indicators
        weekly = mtf.weekly.indicators
        
        # ===== LONG SIGNAL =====
        long_score = self._score_direction(
            mtf=mtf,
            direction=TradeDirection.LONG,
            daily_indicators=daily,
            weekly_indicators=weekly,
            structure_lookback=mtf.daily.ohlcv.tail(50)
        )
        
        # ===== SHORT SIGNAL =====
        short_score = self._score_direction(
            mtf=mtf,
            direction=TradeDirection.SHORT,
            daily_indicators=daily,
            weekly_indicators=weekly,
            structure_lookback=mtf.daily.ohlcv.tail(50)
        )
        
        return long_score, short_score
    
    def _score_direction(
        self,
        mtf: MultiTimeframeData,
        direction: TradeDirection,
        daily_indicators: Dict,
        weekly_indicators: Dict,
        structure_lookback: pd.DataFrame
    ) -> SignalScore:
        """Score single direction (LONG or SHORT)"""
        
        strengths = []
        weaknesses = []
        
        # ===== 1. TREND STRENGTH (30% weight) =====
        adx = daily_indicators.get('adx', [0])
        if isinstance(adx, pd.Series):
            adx_val = adx.iloc[-1]
        else:
            adx_val = 0
        
        er = daily_indicators.get('er', [0])
        if isinstance(er, pd.Series):
            er_val = er.iloc[-1]
        else:
            er_val = 0
        
        # Trend strength scoring
        if adx_val is not None and adx_val > 0:
            if adx_val > 45:
                trend_score = 100
                strengths.append(f"Very strong trend (ADX {adx_val:.0f})")
            elif adx_val > 35:
                trend_score = 85
                strengths.append(f"Strong trend (ADX {adx_val:.0f})")
            elif adx_val > 25:
                trend_score = 70
                strengths.append(f"Trending market (ADX {adx_val:.0f})")
            elif adx_val > 20:
                trend_score = 50
                weaknesses.append(f"Weak trend (ADX {adx_val:.0f})")
            else:
                trend_score = 20
                weaknesses.append(f"Choppy market (ADX {adx_val:.0f})")
        else:
            trend_score = 0
            weaknesses.append("ADX unavailable")
        
        # Efficiency ratio boost
        if er_val is not None and er_val > 0.5:
            trend_score = min(100, trend_score + 15)
            strengths.append(f"Efficient trend (ER {er_val:.2f})")
        elif er_val is not None:
            trend_score = max(0, trend_score - 15)
            weaknesses.append(f"Choppy bars (ER {er_val:.2f})")
        
        # ===== 2. DIRECTION CONFLUENCE (25% weight) =====
        confluence_score = self._score_confluence(direction, mtf, strengths, weaknesses)
        
        # ===== 3. VOLUME QUALITY (20% weight) =====
        volume_score, volume_ratio = self._score_volume(direction, daily_indicators, strengths, weaknesses)
        
        # ===== 4. STRUCTURE QUALITY (15% weight) =====
        structure_score = self._score_structure(direction, structure_lookback, strengths, weaknesses)
        
        # ===== 5. RISK PROFILE (10% weight) =====
        risk_score, atr_pct, pct_200sma = self._score_risk(
            direction, daily_indicators, strengths, weaknesses
        )
        
        # ===== COMPOSITE SCORE =====
        total_score = (
            trend_score * 0.30 +
            confluence_score * 0.25 +
            volume_score * 0.20 +
            structure_score * 0.15 +
            risk_score * 0.10
        )
        
        # Get weekly trend
        weekly_supertrend = weekly_indicators.get('supertrend_direction', [0])
        if isinstance(weekly_supertrend, pd.Series):
            weekly_trend = int(weekly_supertrend.iloc[-1])
        else:
            weekly_trend = 0
        
        return SignalScore(
            symbol=mtf.symbol,
            direction=direction,
            total_score=total_score,
            trend_strength=trend_score,
            direction_confluence=confluence_score,
            volume_quality=volume_score,
            structure_quality=structure_score,
            risk_profile=risk_score,
            adx_value=adx_val or 0,
            volume_ratio=volume_ratio,
            pct_from_200sma=pct_200sma,
            atr_pct=atr_pct,
            weekly_trend=weekly_trend,
            strengths=strengths,
            weaknesses=weaknesses,
        )
    
    def _score_confluence(
        self,
        direction: TradeDirection,
        mtf: MultiTimeframeData,
        strengths: List[str],
        weaknesses: List[str]
    ) -> float:
        """Score multi-TF confluence"""
        
        score = 50  # Base
        
        weekly_200sma = mtf.weekly.latest('close_200_sma')
        weekly_close = mtf.weekly.latest('close')
        weekly_supertrend = mtf.weekly.latest('supertrend_direction')
        
        daily_200sma = mtf.daily.latest('close_200_sma')
        daily_close = mtf.daily.latest('close')
        
        if weekly_200sma is None or weekly_close is None:
            return 30
        
        if direction == TradeDirection.LONG:
            # Check: close > 200 SMA on weekly
            if weekly_close > weekly_200sma:
                score += 25
                strengths.append("Weekly: Price > 200 SMA (bull regime)")
            else:
                score -= 25
                weaknesses.append("Weekly: Price < 200 SMA (bear regime)")
            
            # Check: Supertrend positive
            if weekly_supertrend == 1:
                score += 15
                strengths.append("Weekly: SuperTrend UP")
            else:
                score -= 15
                weaknesses.append("Weekly: SuperTrend DOWN")
            
            # Check: Daily bounce off support
            if daily_close is not None and daily_200sma is not None:
                if daily_close > daily_200sma:
                    score += 10
                    strengths.append("Daily: Price > 200 SMA (support intact)")
        
        else:  # SHORT
            # Check: close < 200 SMA on weekly
            if weekly_close < weekly_200sma:
                score += 25
                strengths.append("Weekly: Price < 200 SMA (bear regime)")
            else:
                score -= 25
                weaknesses.append("Weekly: Price > 200 SMA (bull regime)")
            
            # Check: Supertrend negative
            if weekly_supertrend == -1:
                score += 15
                strengths.append("Weekly: SuperTrend DOWN")
            else:
                score -= 15
                weaknesses.append("Weekly: SuperTrend UP")
            
            # Check: Daily near resistance
            if daily_close is not None and daily_200sma is not None:
                if daily_close < daily_200sma:
                    score += 10
                    strengths.append("Daily: Price < 200 SMA (resistance intact)")
        
        return max(0, min(100, score))
    
    def _score_volume(
        self,
        direction: TradeDirection,
        daily_indicators: Dict,
        strengths: List[str],
        weaknesses: List[str]
    ) -> Tuple[float, float]:
        """Score volume quality"""
        
        score = 50
        
        volume_ratio = daily_indicators.get('volume_ratio', [0])
        if isinstance(volume_ratio, pd.Series):
            vr = volume_ratio.iloc[-1]
        else:
            vr = 0
        
        if vr is not None and vr > 0:
            if vr > 2.0:
                score = 100
                strengths.append(f"VERY STRONG volume (VR {vr:.2f})")
            elif vr > 1.5:
                score = 85
                strengths.append(f"Strong volume (VR {vr:.2f})")
            elif vr > 1.0:
                score = 60
                strengths.append(f"Normal volume (VR {vr:.2f})")
            elif vr > 0.7:
                score = 35
                weaknesses.append(f"Low volume (VR {vr:.2f})")
            else:
                score = 10
                weaknesses.append(f"Very low volume (VR {vr:.2f})")
        
        return score, vr
    
    def _score_structure(
        self,
        direction: TradeDirection,
        df: pd.DataFrame,
        strengths: List[str],
        weaknesses: List[str]
    ) -> float:
        """Score structure quality (ChoCH/BOS/levels)"""
        
        score = 50
        
        # ChoCH detection
        choch, _ = self.classifier.detect_choch(df)
        if choch:
            score += 20
            strengths.append("ChoCH detected (reversal confirmation)")
        
        # BOS detection
        bos, _ = self.classifier.detect_bos(df)
        if bos:
            score += 15
            strengths.append("BOS detected (structure break)")
        
        # Structure integrity
        structure = self.classifier.classify_structure(df)
        
        if direction == TradeDirection.LONG:
            if "LL" in structure.formation or structure.direction == 1:
                score += 10
                strengths.append(f"Bullish structure ({structure.formation})")
            elif "HH" in structure.formation and "LOWER" not in structure.formation:
                score += 5
        
        else:  # SHORT
            if "HH" in structure.formation or (structure.direction == -1):
                score += 10
                strengths.append(f"Bearish structure ({structure.formation})")
            elif "LL" in structure.formation:
                score += 5
        
        return max(0, min(100, score))
    
    def _score_risk(
        self,
        direction: TradeDirection,
        daily_indicators: Dict,
        strengths: List[str],
        weaknesses: List[str]
    ) -> Tuple[float, float, float]:
        """Score risk profile (volatility, mean reversion)"""
        
        score = 50
        
        # ATR% volatility
        atr_pct = daily_indicators.get('atr_pct', [0])
        if isinstance(atr_pct, pd.Series):
            atr_p = atr_pct.iloc[-1]
        else:
            atr_p = 0
        
        if atr_p is not None and atr_p > 0:
            if atr_p < 1.0:
                score += 15
                strengths.append(f"Low volatility (ATR% {atr_p:.2f})")
            elif atr_p < 2.0:
                score += 10
            elif atr_p < 4.0:
                score += 0
            else:
                score -= 10
                weaknesses.append(f"High volatility (ATR% {atr_p:.2f})")
        
        # % from 200 SMA (mean reversion check)
        pct_200sma = daily_indicators.get('pct_from_200sma', [0])
        if isinstance(pct_200sma, pd.Series):
            pct_200 = pct_200sma.iloc[-1]
        else:
            pct_200 = 0
        
        if pct_200 is not None:
            if direction == TradeDirection.LONG:
                if pct_200 < -25:
                    score += 20
                    strengths.append(f"Deep reversion (% from 200 SMA: {pct_200:.1f}%)")
                elif pct_200 < 0:
                    score += 10
                elif pct_200 > 25:
                    score -= 20
                    weaknesses.append(f"Overextended (% from 200 SMA: {pct_200:.1f}%)")
            else:  # SHORT
                if pct_200 > 25:
                    score += 20
                    strengths.append(f"Deep reversion (% from 200 SMA: {pct_200:.1f}%)")
                elif pct_200 > 0:
                    score += 10
                elif pct_200 < -25:
                    score -= 20
                    weaknesses.append(f"Overextended (% from 200 SMA: {pct_200:.1f}%)")
        
        return max(0, min(100, score)), atr_p, pct_200
    
    def rank_signals(self, scores: List[SignalScore], direction: TradeDirection = None) -> List[SignalScore]:
        """
        Rank signals by score
        
        Args:
            scores: List of SignalScore objects
            direction: Filter to LONG/SHORT only (None = all)
        
        Returns:
            Sorted by total_score descending
        """
        filtered = scores
        
        if direction:
            filtered = [s for s in scores if s.direction == direction]
        
        return sorted(filtered, key=lambda s: s.total_score, reverse=True)


# ==================== EXAMPLE USAGE ====================

def example_signal_scoring():
    """Example: Score signals for multiple symbols"""
    from .multi_timeframe import MultiTimeframeLayer
    
    mtf_layer = MultiTimeframeLayer()
    scorer = ScoringEngine()
    
    symbols = ["SPY", "QQQ"]
    all_long_scores = []
    all_short_scores = []
    
    print(f"\n{'='*70}")
    print(f"🎯 SIGNAL SCORING ENGINE - Multi-Timeframe Analysis")
    print(f"{'='*70}\n")
    
    for symbol in symbols:
        print(f"📊 Analyzing {symbol}...")
        
        mtf = mtf_layer.fetch_symbol_mtf(symbol)
        long_score, short_score = scorer.score_mtf_signal(mtf)
        
        all_long_scores.append(long_score)
        all_short_scores.append(short_score)
        
        # Display
        print(f"\n  🟢 LONG Score: {long_score.total_score:.0f}/100")
        print(f"     Trend: {long_score.trend_strength:.0f} | Conf: {long_score.direction_confluence:.0f} | Vol: {long_score.volume_quality:.0f}")
        if long_score.strengths:
            for s in long_score.strengths[:2]:
                print(f"     ✓ {s}")
        
        print(f"\n  🔴 SHORT Score: {short_score.total_score:.0f}/100")
        print(f"     Trend: {short_score.trend_strength:.0f} | Conf: {short_score.direction_confluence:.0f} | Vol: {short_score.volume_quality:.0f}")
        if short_score.strengths:
            for s in short_score.strengths[:2]:
                print(f"     ✓ {s}")
    
    # Rank all
    print(f"\n{'='*70}")
    print(f"📈 LONG SIGNALS - Ranked")
    print(f"{'='*70}")
    
    ranked_long = scorer.rank_signals(all_long_scores)
    for i, score in enumerate(ranked_long, 1):
        print(f"{i}. {score.symbol:6} - Score: {score.total_score:.0f}/100 | ADX: {score.adx_value:.0f} | VR: {score.volume_ratio:.2f}")
    
    print(f"\n{'='*70}")
    print(f"📉 SHORT SIGNALS - Ranked")
    print(f"{'='*70}")
    
    ranked_short = scorer.rank_signals(all_short_scores)
    for i, score in enumerate(ranked_short, 1):
        print(f"{i}. {score.symbol:6} - Score: {score.total_score:.0f}/100 | ADX: {score.adx_value:.0f} | VR: {score.volume_ratio:.2f}")


if __name__ == "__main__":
    example_signal_scoring()
