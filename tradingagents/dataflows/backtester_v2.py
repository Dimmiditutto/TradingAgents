"""
backtester_v2.py - Advanced Backtest with 12 Metrics & Breakdown
Upgraded from swing_system with complete analytics

12 Metriche:
  1. Total Trades
  2. Win Rate (%)
  3. Profit Factor
  4. Average R/R realized
  5. Total PnL %
  6. CAGR (Compound Annual Growth Rate)
  7. Sharpe Ratio
  8. Sortino Ratio
  9. Max Drawdown (%)
  10. Average Drawdown (%)
  11. Max Consecutive Losses
  12. Equity Curve

Breakdown per:
  - Tipo evento (BOS_UP, BOS_DOWN, CHoCH_UP, CHoCH_DOWN)
  - Direzione (LONG, SHORT)
  - Score bucket (60-69, 70-79, 80-89, 90+)
  - Durata (1-3gg, 4-7gg, 8-10gg)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


# ==================== TRADE DATACLASS ====================

@dataclass
class Trade:
    """Una singola trade simulata."""
    ticker: str
    direction: str
    entry_idx: int
    entry_date: pd.Timestamp
    entry_price: float
    entry_score: float
    stop_loss: float
    target1: float
    target2: float
    
    exit_idx: Optional[int] = None
    exit_date: Optional[pd.Timestamp] = None
    exit_price: float = 0.0
    exit_reason: str = ""        # TARGET1, TARGET2, STOP, TIMEOUT
    pnl_pct: float = 0.0
    rr_realized: float = 0.0
    n_bars_held: int = 0
    won: bool = False
    
    # Contesto
    structure_event: str = ""
    volume_ratio: float = 0.0
    adx: float = 0.0
    atr_pct: float = 0.0
    score: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "direction": self.direction,
            "entry_date": str(self.entry_date.date()),
            "exit_date": str(self.exit_date.date()) if self.exit_date else "",
            "entry_price": round(self.entry_price, 4),
            "exit_price": round(self.exit_price, 4),
            "stop_loss": round(self.stop_loss, 4),
            "target": round(self.target1, 4),
            "exit_reason": self.exit_reason,
            "pnl_pct": round(self.pnl_pct, 3),
            "rr_realized": round(self.rr_realized, 2),
            "n_bars_held": self.n_bars_held,
            "won": int(self.won),
            "score": round(self.score, 1),
            "structure_event": self.structure_event,
            "volume_ratio": round(self.volume_ratio, 2),
            "adx": round(self.adx, 1),
            "atr_pct": round(self.atr_pct, 2),
        }


# ==================== BACKTEST RESULT DATACLASS ====================

@dataclass
class BacktestResult:
    """Risultato completo del backtest."""
    ticker: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    
    trades: List[Trade] = field(default_factory=list)
    
    # 12 Metriche
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_rr_realized: float = 0.0
    total_pnl_pct: float = 0.0
    cagr: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    max_consecutive_losses: int = 0
    
    equity_curve: List[Dict] = field(default_factory=list)
    
    # Breakdown
    breakdown_by_event: Dict = field(default_factory=dict)
    breakdown_by_direction: Dict = field(default_factory=dict)
    breakdown_by_score: Dict = field(default_factory=dict)
    breakdown_by_duration: Dict = field(default_factory=dict)
    
    def calculate_metrics(self) -> None:
        """Calcola tutte le metriche dai trades."""
        if not self.trades:
            return
        
        # Count
        self.total_trades = len(self.trades)
        self.winning_trades = sum(1 for t in self.trades if t.won)
        self.losing_trades = self.total_trades - self.winning_trades
        
        # Win Rate
        self.win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
        
        # Profit Factor
        wins = sum(t.pnl_pct for t in self.trades if t.won)
        losses = sum(t.pnl_pct for t in self.trades if not t.won)
        self.profit_factor = wins / abs(losses) if losses != 0 else (wins if wins > 0 else 0)
        
        # Avg R/R realized
        rr_values = [t.rr_realized for t in self.trades if t.rr_realized > 0]
        self.avg_rr_realized = np.mean(rr_values) if rr_values else 0.0
        
        # Total PnL %
        self.total_pnl_pct = sum(t.pnl_pct for t in self.trades)
        
        # CAGR
        if self.total_pnl_pct > 0:
            years = (self.end_date - self.start_date).days / 365.25
            self.cagr = ((1 + self.total_pnl_pct / 100) ** (1 / max(years, 1)) - 1) * 100
        
        # Sharpe Ratio
        returns = [t.pnl_pct for t in self.trades]
        if len(returns) > 1:
            self.sharpe_ratio = (np.mean(returns) / (np.std(returns) + 0.0001)) * np.sqrt(252)
        
        # Sortino Ratio (downside deviation)
        downside = [r for r in returns if r < 0]
        if downside:
            downside_vol = np.std(downside)
            self.sortino_ratio = (np.mean(returns) / (downside_vol + 0.0001)) * np.sqrt(252)
        
        # Drawdown
        self._calculate_drawdown()
        
        # Max consecutive losses
        self._calculate_max_consecutive()
    
    def _calculate_drawdown(self) -> None:
        """Calcola max drawdown e average drawdown."""
        if not self.equity_curve:
            return
        
        equities = [e["equity"] for e in self.equity_curve]
        drawdowns = []
        peak = equities[0]
        max_dd = 0.0
        
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100 if peak > 0 else 0.0
            drawdowns.append(dd)
            max_dd = max(max_dd, dd)
        
        self.max_drawdown = max_dd
        self.avg_drawdown = np.mean(drawdowns) if drawdowns else 0.0
    
    def _calculate_max_consecutive(self) -> None:
        """Calcola max consecutive losses."""
        if not self.trades:
            return
        
        consecutive = 0
        max_consecutive = 0
        
        for trade in self.trades:
            if not trade.won:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0
        
        self.max_consecutive_losses = max_consecutive
    
    def to_dict(self) -> dict:
        start = pd.Timestamp(self.start_date)
        end = pd.Timestamp(self.end_date)
        return {
            "ticker": self.ticker,
            "period": f"{start.date()} to {end.date()}",
            "metrics": {
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": round(self.win_rate, 1),
                "profit_factor": round(self.profit_factor, 2),
                "avg_rr_realized": round(self.avg_rr_realized, 2),
                "total_pnl_pct": round(self.total_pnl_pct, 2),
                "cagr": round(self.cagr, 2),
                "sharpe_ratio": round(self.sharpe_ratio, 2),
                "sortino_ratio": round(self.sortino_ratio, 2),
                "max_drawdown": round(self.max_drawdown, 2),
                "avg_drawdown": round(self.avg_drawdown, 2),
                "max_consecutive_losses": self.max_consecutive_losses,
            },
            "trades": [t.to_dict() for t in self.trades],
            "breakdown": {
                "by_event": self.breakdown_by_event,
                "by_direction": self.breakdown_by_direction,
                "by_score": self.breakdown_by_score,
                "by_duration": self.breakdown_by_duration,
            }
        }


# ==================== BACKTEST ENGINE ====================

class BacktesterV2:
    """Engine di backtest walk-forward con no-lookahead bias."""
    
    def __init__(self,
                 min_signal_score: float = 70.0,
                 max_hold_days: int = 7,
                 risk_per_trade_pct: float = 1.0):
        """
        Args:
            min_signal_score: score minimo per entry (70-100)
            max_hold_days: massimo giorni per tenir open una trade
            risk_per_trade_pct: % di rischio per trade (default 1%)
        """
        self.min_signal_score = min_signal_score
        self.max_hold_days = max_hold_days
        self.risk_per_trade_pct = risk_per_trade_pct
    
    def run_backtest(self,
                    ticker: str,
                    df: pd.DataFrame,
                    start_date: pd.Timestamp,
                    end_date: pd.Timestamp,
                    scoring_fn=None) -> BacktestResult:
        """
        Esegue backtest walk-forward su dati storici.
        
        Args:
            ticker: simbolo
            df: DataFrame giornaliero (deve avere indicatori e struttura già calcolati)
            start_date: data inizio backtest
            end_date: data fine backtest
            scoring_fn: funzione score(row_df) -> score 0-100, direction, details
        
        Returns:
            BacktestResult con tutte le metriche
        """
        result = BacktestResult(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Convert dates to Timestamp if needed
        start_date = pd.Timestamp(start_date)
        end_date = pd.Timestamp(end_date)

        # Filter dataframe al range
        mask = (df.index >= start_date) & (df.index <= end_date)
        df_range = df[mask].copy()

        if len(df_range) < 100:
            return result

        trades = []
        equity = 100.0  # Starting equity
        equity_curve = [{"date": df_range.index[0].strftime("%Y-%m-%d"), "equity": equity}]
        open_trade = None
        
        # Walk forward through each bar
        for i in range(len(df_range)):
            current_date = df_range.index[i]
            current_close = df_range["close"].iloc[i]
            current_volume = df_range["volume"].iloc[i] if "volume" in df_range.columns else 0
            
            # Check if open trade hits stop/target
            if open_trade:
                bars_held = i - open_trade.entry_idx
                
                # Check targets
                if current_close >= open_trade.target1 and open_trade.direction == "LONG":
                    open_trade.exit_idx = i
                    open_trade.exit_date = current_date
                    open_trade.exit_price = open_trade.target1
                    open_trade.exit_reason = "TARGET"
                    open_trade.n_bars_held = bars_held
                    open_trade.won = True
                elif current_close <= open_trade.target1 and open_trade.direction == "SHORT":
                    open_trade.exit_idx = i
                    open_trade.exit_date = current_date
                    open_trade.exit_price = open_trade.target1
                    open_trade.exit_reason = "TARGET"
                    open_trade.n_bars_held = bars_held
                    open_trade.won = True
                
                # Check stops
                elif current_close <= open_trade.stop_loss and open_trade.direction == "LONG":
                    open_trade.exit_idx = i
                    open_trade.exit_date = current_date
                    open_trade.exit_price = open_trade.stop_loss
                    open_trade.exit_reason = "STOP"
                    open_trade.n_bars_held = bars_held
                    open_trade.won = False
                elif current_close >= open_trade.stop_loss and open_trade.direction == "SHORT":
                    open_trade.exit_idx = i
                    open_trade.exit_date = current_date
                    open_trade.exit_price = open_trade.stop_loss
                    open_trade.exit_reason = "STOP"
                    open_trade.n_bars_held = bars_held
                    open_trade.won = False
                
                # Check timeout
                elif bars_held >= self.max_hold_days:
                    open_trade.exit_idx = i
                    open_trade.exit_date = current_date
                    open_trade.exit_price = current_close
                    open_trade.exit_reason = "TIMEOUT"
                    open_trade.n_bars_held = bars_held
                    open_trade.won = current_close > open_trade.entry_price if open_trade.direction == "LONG" else current_close < open_trade.entry_price
                
                # Close trade updates
                if open_trade.exit_price > 0:
                    risk = abs(open_trade.entry_price - open_trade.stop_loss)
                    if open_trade.direction == "LONG":
                        open_trade.pnl_pct = ((open_trade.exit_price - open_trade.entry_price) / open_trade.entry_price) * 100
                    else:
                        open_trade.pnl_pct = ((open_trade.entry_price - open_trade.exit_price) / open_trade.entry_price) * 100
                    
                    open_trade.rr_realized = abs(open_trade.exit_price - open_trade.entry_price) / (risk + 0.0001)
                    
                    trades.append(open_trade)
                    
                    # Update equity
                    equity *= (1 + open_trade.pnl_pct / 100)
                    
                    open_trade = None
            
            # Look for new entry signals
            if open_trade is None and scoring_fn:
                try:
                    # Score usando solo dati fino a i (no lookahead)
                    df_subset = df_range.iloc[:i+1]
                    score_data = scoring_fn(df_subset)

                    if isinstance(score_data, list):
                        candidates = [s for s in score_data if s is not None and getattr(s, "filters_passed", True)]
                        if candidates:
                            best = max(candidates, key=lambda s: s.score)
                            score_data = {
                                "score": best.score,
                                "direction": best.direction,
                                "stop_loss": best.stop_loss,
                                "target1": best.target1,
                                "target2": best.target2,
                                "structure_event": best.structure_event,
                                "volume_ratio": best.volume_ratio,
                                "adx": best.adx,
                                "atr_pct": best.atr_pct,
                            }
                        else:
                            score_data = None
                    elif hasattr(score_data, "score"):
                        score_data = {
                            "score": score_data.score,
                            "direction": score_data.direction,
                            "stop_loss": score_data.stop_loss,
                            "target1": score_data.target1,
                            "target2": score_data.target2,
                            "structure_event": score_data.structure_event,
                            "volume_ratio": score_data.volume_ratio,
                            "adx": score_data.adx,
                            "atr_pct": score_data.atr_pct,
                        }
                    elif score_data is not None and not isinstance(score_data, dict):
                        score_data = None
                    
                    if score_data and score_data["score"] >= self.min_signal_score:
                        direction = score_data.get("direction", "LONG")
                        
                        open_trade = Trade(
                            ticker=ticker,
                            direction=direction,
                            entry_idx=i,
                            entry_date=current_date,
                            entry_price=current_close,
                            entry_score=score_data["score"],
                            stop_loss=score_data["stop_loss"],
                            target1=score_data["target1"],
                            target2=score_data.get("target2", score_data["target1"]),
                            structure_event=score_data.get("structure_event", ""),
                            volume_ratio=score_data.get("volume_ratio", 1.0),
                            adx=score_data.get("adx", 0.0),
                            atr_pct=score_data.get("atr_pct", 1.0),
                            score=score_data["score"],
                        )
                except:
                    pass
            
            # Update equity curve
            equity_curve.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "equity": equity
            })
        
        result.trades = trades
        result.equity_curve = equity_curve
        result.calculate_metrics()
        self._calculate_breakdown(result)
        
        return result
    
    def _calculate_breakdown(self, result: BacktestResult) -> None:
        """Calcola breakdown per event/direction/score/duration."""
        # By event
        for event in ["BOS_UP", "BOS_DOWN", "CHoCH_UP", "CHoCH_DOWN"]:
            trades_event = [t for t in result.trades if t.structure_event == event]
            if trades_event:
                result.breakdown_by_event[event] = {
                    "count": len(trades_event),
                    "win_rate": sum(1 for t in trades_event if t.won) / len(trades_event) * 100,
                    "avg_pnl": np.mean([t.pnl_pct for t in trades_event]),
                }
        
        # By direction
        for direction in ["LONG", "SHORT"]:
            trades_dir = [t for t in result.trades if t.direction == direction]
            if trades_dir:
                result.breakdown_by_direction[direction] = {
                    "count": len(trades_dir),
                    "win_rate": sum(1 for t in trades_dir if t.won) / len(trades_dir) * 100,
                    "avg_pnl": np.mean([t.pnl_pct for t in trades_dir]),
                }
        
        # By score bucket
        for bucket in ["60-69", "70-79", "80-89", "90+"]:
            bounds = {"60-69": (60, 70), "70-79": (70, 80), "80-89": (80, 90), "90+": (90, 101)}
            lo, hi = bounds[bucket]
            trades_score = [t for t in result.trades if lo <= t.score < hi]
            if trades_score:
                result.breakdown_by_score[bucket] = {
                    "count": len(trades_score),
                    "win_rate": sum(1 for t in trades_score if t.won) / len(trades_score) * 100,
                    "avg_pnl": np.mean([t.pnl_pct for t in trades_score]),
                }
        
        # By duration
        for duration in ["1-3gg", "4-7gg", "8-10gg"]:
            bounds = {"1-3gg": (1, 4), "4-7gg": (4, 8), "8-10gg": (8, 11)}
            lo, hi = bounds[duration]
            trades_dur = [t for t in result.trades if lo <= t.n_bars_held < hi]
            if trades_dur:
                result.breakdown_by_duration[duration] = {
                    "count": len(trades_dur),
                    "win_rate": sum(1 for t in trades_dur if t.won) / len(trades_dur) * 100,
                    "avg_pnl": np.mean([t.pnl_pct for t in trades_dur]),
                }


# ==================== UTILITY FUNCTIONS ====================

def print_backtest_report(result: BacktestResult) -> None:
    """Stampa report testuale."""
    print("\n" + "="*60)
    print(f"BACKTEST REPORT: {result.ticker}")
    print("="*60)
    print(f"\nMetriche:")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Winning: {result.winning_trades} ({result.win_rate:.1f}%)")
    print(f"  Losing: {result.losing_trades}")
    print(f"  Profit Factor: {result.profit_factor:.2f}")
    print(f"  Avg R/R: {result.avg_rr_realized:.2f}")
    print(f"  Total PnL %: {result.total_pnl_pct:.2f}%")
    print(f"  CAGR: {result.cagr:.2f}%")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Sortino Ratio: {result.sortino_ratio:.2f}")
    print(f"  Max Drawdown: {result.max_drawdown:.2f}%")
    print(f"  Avg Drawdown: {result.avg_drawdown:.2f}%")
    print(f"  Max Consecutive Losses: {result.max_consecutive_losses}")
    
    if result.breakdown_by_event:
        print(f"\nBreakdown by Event:")
        for event, data in result.breakdown_by_event.items():
            print(f"  {event}: {data['count']} trades, WR={data['win_rate']:.1f}%, Avg={data['avg_pnl']:.2f}%")
    
    print("\n" + "="*60)
