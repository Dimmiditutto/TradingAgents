"""
backtest.py  —  MTF Swing System
─────────────────────────────────
Backtest completo con walk-forward, no-lookahead.

METRICHE OUTPUT:
  Win Rate          — % trade in profitto
  Profit Factor     — gross profit / gross loss
  Avg R/R           — media del R/R realizzato
  Total PnL %       — rendimento cumulato simulato (size fissa)
  CAGR              — compound annual growth rate
  Sharpe Ratio      — excess return / volatilità (rf=0)
  Sortino Ratio     — excess return / downside deviation
  Max Drawdown      — picco → valle massimo sull'equity curve
  Avg Drawdown      — media dei drawdown
  Total Trades      — numero trade totali
  Equity Chart      — serie temporale dell'equity (per la dashboard)

  Breakdown per:
    - Tipo evento strutturale (CHoCH_UP / BOS_UP / ...)
    - Direzione (LONG / SHORT)
    - Score bucket (60-69 / 70-79 / 80-89 / 90+)
    - Durata (1-3gg / 4-7gg / 8-10gg)

METODOLOGIA NO-LOOKAHEAD:
  Per ogni barra i (a partire da warmup_bars):
    - Indicatori calcolati su df[:i+1]
    - Struttura calcolata su df[:i+1]
    - Segnale generato con solo dati disponibili fino a i
    - Simulazione uscita su barre i+1 … i+max_days
"""

from dataclasses import dataclass, field
from typing import Optional
import json
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from indicators import compute_all
from market_structure import analyze as analyze_structure
from scoring import score_ticker, DEFAULT_FILTERS, DEFAULT_WEIGHTS, DEFAULT_TRADE


# ──────────────────────────────────────────────────────────────────────────────
# TRADE DATACLASS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    ticker:          str
    direction:       str
    entry_date:      pd.Timestamp
    entry_price:     float
    stop_loss:       float
    target1:         float
    target2:         float
    score:           float
    structure_event: str
    volume_ratio:    float
    adx:             float
    atr_pct:         float

    exit_date:    Optional[pd.Timestamp] = None
    exit_price:   float = 0.0
    exit_reason:  str   = ""      # T1 | T2 | STOP | TIMEOUT
    pnl_pct:      float = 0.0    # % sul capitale (size fissa 1 unità)
    rr_realized:  float = 0.0
    n_bars_held:  int   = 0
    won:          bool  = False

    def to_dict(self) -> dict:
        return {
            "ticker":          self.ticker,
            "direction":       self.direction,
            "entry_date":      str(self.entry_date.date()),
            "exit_date":       str(self.exit_date.date()) if self.exit_date else "",
            "entry_price":     round(self.entry_price, 4),
            "exit_price":      round(self.exit_price, 4),
            "stop_loss":       round(self.stop_loss, 4),
            "target1":         round(self.target1, 4),
            "exit_reason":     self.exit_reason,
            "pnl_pct":         round(self.pnl_pct, 3),
            "rr_realized":     round(self.rr_realized, 2),
            "n_bars_held":     self.n_bars_held,
            "won":             int(self.won),
            "score":           round(self.score, 1),
            "structure_event": self.structure_event,
            "volume_ratio":    round(self.volume_ratio, 2),
            "adx":             round(self.adx, 1),
            "atr_pct":         round(self.atr_pct, 2),
        }


# ──────────────────────────────────────────────────────────────────────────────
# SIMULAZIONE USCITA
# ──────────────────────────────────────────────────────────────────────────────

def simulate_trade(df: pd.DataFrame,
                   entry_bar: int,
                   direction: str,
                   entry: float, stop: float,
                   t1: float, t2: float,
                   max_days: int = 7) -> tuple[float, float, str, int]:
    """
    Simula l'uscita barra per barra. Logica:
      LONG : tocco stop (low<=stop) → -1R | T1 (high>=t1) | T2 (high>=t2) | timeout
      SHORT: tocco stop (high>=stop) → -1R | T1 (low<=t1) | T2 (low<=t2) | timeout
    Ritorna (exit_price, rr_realized, reason, n_bars).
    """
    is_long = direction == "LONG"
    risk    = abs(entry - stop)
    n       = len(df)
    highs   = df["high"].values
    lows    = df["low"].values
    closes  = df["close"].values

    for bar in range(entry_bar + 1, min(entry_bar + max_days + 1, n)):
        nb = bar - entry_bar
        h, l = highs[bar], lows[bar]

        if is_long:
            if l <= stop:   return stop, -1.0,                                  "STOP",    nb
            if h >= t2:     return t2,   (t2 - entry) / max(risk, 1e-10),      "T2",      nb
            if h >= t1:     return t1,   (t1 - entry) / max(risk, 1e-10),      "T1",      nb
        else:
            if h >= stop:   return stop, -1.0,                                  "STOP",    nb
            if l <= t2:     return t2,   (entry - t2) / max(risk, 1e-10),      "T2",      nb
            if l <= t1:     return t1,   (entry - t1) / max(risk, 1e-10),      "T1",      nb

    last = min(entry_bar + max_days, n - 1)
    ep   = closes[last]
    rr   = ((ep - entry) if is_long else (entry - ep)) / max(risk, 1e-10)
    return ep, rr, "TIMEOUT", last - entry_bar


# ──────────────────────────────────────────────────────────────────────────────
# BACKTEST SINGOLO TICKER
# ──────────────────────────────────────────────────────────────────────────────

def backtest_ticker(ticker: str,
                    df_raw: pd.DataFrame,
                    warmup: int = 252,
                    min_score: float = 60.0,
                    max_days: int = 7,
                    step: int = 1,
                    filters: dict = None,
                    weights: dict = None,
                    trade_params: dict = None) -> list[Trade]:

    if len(df_raw) < warmup + 20:
        return []

    df   = compute_all(df_raw)
    n    = len(df)
    out  = []

    for i in range(warmup, n - max_days - 1, step):
        sl = df.iloc[:i + 1]
        try:
            res = analyze_structure(sl, include_weekly=True)
            mtf = res.get("mtf", {})
        except Exception:
            continue
        if not mtf:
            continue

        for direction in ("LONG", "SHORT"):
            sig = score_ticker(ticker, sl, mtf,
                               direction=direction,
                               filters=filters or DEFAULT_FILTERS,
                               weights=weights or DEFAULT_WEIGHTS,
                               trade_params=trade_params or DEFAULT_TRADE,
                               min_score=min_score)
            if sig is None:
                continue

            ep, rr, reason, nb = simulate_trade(
                df, i, direction,
                sig.entry_price, sig.stop_loss,
                sig.target1, sig.target2,
                max_days=max_days
            )

            pnl = ((ep - sig.entry_price) / sig.entry_price * 100
                   if direction == "LONG"
                   else (sig.entry_price - ep) / sig.entry_price * 100)

            exit_idx = min(i + nb, n - 1)
            out.append(Trade(
                ticker=ticker, direction=direction,
                entry_date=df.index[i], entry_price=sig.entry_price,
                stop_loss=sig.stop_loss, target1=sig.target1, target2=sig.target2,
                score=sig.score, structure_event=sig.structure_event,
                volume_ratio=sig.volume_ratio, adx=sig.adx, atr_pct=sig.atr_pct,
                exit_date=df.index[exit_idx], exit_price=ep,
                exit_reason=reason, pnl_pct=round(pnl, 4),
                rr_realized=round(rr, 3),
                n_bars_held=nb, won=rr > 0,
            ))
    return out


# ──────────────────────────────────────────────────────────────────────────────
# METRICHE COMPLETE
# ──────────────────────────────────────────────────────────────────────────────

def compute_stats(trades: list[Trade], risk_per_trade_pct: float = 1.0) -> dict:
    """
    Calcola tutte le metriche di backtest.

    risk_per_trade_pct: % del capitale rischiato per trade (per equity curve).
    Con 1%: ogni stop perso = -1%, ogni T1 (RR=1.33) = +1.33%, ecc.
    """
    if not trades:
        return {"error": "Nessun trade"}

    df = pd.DataFrame([t.to_dict() for t in trades])
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["exit_date"]  = pd.to_datetime(df["exit_date"])
    df = df.sort_values("entry_date").reset_index(drop=True)

    n       = len(df)
    n_won   = int(df["won"].sum())
    wr      = n_won / n * 100

    # ── PnL basato su R/R realizzato × rischio per trade
    # Più realistico di usare pnl_pct grezzo (che dipende dal prezzo assoluto)
    df["pnl_r"] = df["rr_realized"] * risk_per_trade_pct   # % del portafoglio

    gross_p = df["pnl_r"][df["pnl_r"] > 0].sum()
    gross_l = df["pnl_r"][df["pnl_r"] < 0].abs().sum()
    pf      = gross_p / max(gross_l, 1e-10)

    # ── Equity curve (composta)
    equity = [100.0]
    for pnl in df["pnl_r"]:
        equity.append(equity[-1] * (1 + pnl / 100))
    equity = np.array(equity[1:])   # stessa lunghezza di df

    total_return = (equity[-1] - 100) / 100 * 100   # %

    # ── CAGR
    first_date = df["entry_date"].iloc[0]
    last_date  = df["exit_date"].iloc[-1]
    years      = max((last_date - first_date).days / 365.25, 0.01)
    cagr       = ((equity[-1] / 100) ** (1 / years) - 1) * 100

    # ── Drawdown
    peak     = np.maximum.accumulate(equity)
    dd_pct   = (equity - peak) / peak * 100           # sempre <= 0
    max_dd   = float(dd_pct.min())
    avg_dd   = float(dd_pct[dd_pct < 0].mean()) if (dd_pct < 0).any() else 0.0

    # ── Sharpe (daily returns, rf=0)
    daily_ret = pd.Series(df["pnl_r"].values)
    sharpe    = (daily_ret.mean() / max(daily_ret.std(), 1e-10)) * np.sqrt(252)

    # ── Sortino (solo downside deviation)
    neg        = daily_ret[daily_ret < 0]
    down_dev   = neg.std() if len(neg) > 1 else 1e-10
    sortino    = (daily_ret.mean() / max(down_dev, 1e-10)) * np.sqrt(252)

    # ── Avg R/R
    avg_rr = float(df["rr_realized"].mean())

    # ── Durata media
    avg_hold = float(df["n_bars_held"].mean())

    # ── Equity chart series (per plotting in dashboard)
    equity_series = [
        {"date": str(d.date()), "equity": round(float(e), 4)}
        for d, e in zip(df["exit_date"], equity)
    ]

    # ── Breakdown per evento strutturale
    def breakdown(group_col: str) -> dict:
        g = df.groupby(group_col)
        res = {}
        for name, grp in g:
            n_g   = len(grp)
            wr_g  = grp["won"].mean() * 100
            pnl_g = grp["pnl_r"].sum()
            rr_g  = grp["rr_realized"].mean()
            res[str(name)] = {
                "count":    n_g,
                "win_rate": round(wr_g, 1),
                "total_pnl_r": round(pnl_g, 2),
                "avg_rr":   round(rr_g, 2),
            }
        return res

    # Score bucket — gestisce NaN
    df["score_clean"] = df["score"].fillna(0)
    df["score_bucket"] = (((df["score_clean"] // 10) * 10).astype(int).astype(str) + "-" +
                          ((df["score_clean"] // 10) * 10 + 9).astype(int).astype(str))

    # Hold duration bucket
    def dur_bucket(n):
        if n <= 3:  return "1-3g"
        if n <= 7:  return "4-7g"
        return "8+g"
    df["dur_bucket"] = df["n_bars_held"].apply(dur_bucket)

    return {
        "summary": {
            "total_trades":   n,
            "n_won":          n_won,
            "win_rate_pct":   round(wr, 1),
            "profit_factor":  round(pf, 2),
            "avg_rr":         round(avg_rr, 2),
            "total_pnl_pct":  round(total_return, 2),
            "cagr_pct":       round(cagr, 2),
            "sharpe":         round(sharpe, 2),
            "sortino":        round(sortino, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "avg_drawdown_pct": round(avg_dd, 2),
            "avg_hold_days":  round(avg_hold, 1),
            "gross_profit_r": round(gross_p, 2),
            "gross_loss_r":   round(gross_l, 2),
            "years_tested":   round(years, 1),
            "risk_per_trade": risk_per_trade_pct,
        },
        "equity_series":      equity_series,
        "by_event":           breakdown("structure_event"),
        "by_direction":       breakdown("direction"),
        "by_score_bucket":    breakdown("score_bucket"),
        "by_duration":        breakdown("dur_bucket"),
        "by_exit_reason":     breakdown("exit_reason"),
        "trades_sample":      df.head(200).to_dict("records"),   # per tabella
    }


def print_report(stats: dict) -> None:
    if "error" in stats:
        print(f"[ERROR] {stats['error']}"); return

    s = stats["summary"]
    w = 58
    def row(label, value, color=""):
        print(f"  {label:<28} {value}")

    print("\n" + "═" * w)
    print("  BACKTEST REPORT — MTF Swing System")
    print("═" * w)
    row("Trade totali",        f"{s['total_trades']:>8}")
    row("Win rate",            f"{s['win_rate_pct']:>7.1f}%")
    row("Profit Factor",       f"{s['profit_factor']:>8.2f}")
    row("Avg R/R",             f"{s['avg_rr']:>+8.2f}")
    print(f"  {'─'*44}")
    row("Total PnL",           f"{s['total_pnl_pct']:>+7.2f}%")
    row("CAGR",                f"{s['cagr_pct']:>+7.2f}%  ({s['years_tested']:.1f} anni)")
    row("Sharpe Ratio",        f"{s['sharpe']:>8.2f}")
    row("Sortino Ratio",       f"{s['sortino']:>8.2f}")
    print(f"  {'─'*44}")
    row("Max Drawdown",        f"{s['max_drawdown_pct']:>7.2f}%")
    row("Avg Drawdown",        f"{s['avg_drawdown_pct']:>7.2f}%")
    row("Durata media",        f"{s['avg_hold_days']:>6.1f} giorni")
    row("Rischio per trade",   f"{s['risk_per_trade']:>7.1f}%  del capitale")
    print(f"  {'─'*44}")

    if "by_event" in stats:
        print("  Evento strutturale:")
        for evt, d in stats["by_event"].items():
            if evt:
                print(f"    {evt:<18} n={d['count']:3d}  WR={d['win_rate']:>5.1f}%  "
                      f"RR={d['avg_rr']:>+5.2f}  PnL={d['total_pnl_r']:>+6.2f}R")
    print(f"  {'─'*44}")
    if "by_score_bucket" in stats:
        print("  Score → Win rate:")
        for bucket, d in sorted(stats["by_score_bucket"].items()):
            bar = "█" * int(d["win_rate"] / 5)
            print(f"    {bucket:<8}  WR={d['win_rate']:>5.1f}%  n={d['count']:3d}  {bar}")
    print("═" * w)


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data_layer import generate_synthetic
    import random

    print("Backtest su dati sintetici — 3 ticker, trend rialzista\n")
    all_trades = []

    for ticker, seed in [("AAPL", 1), ("MSFT", 2), ("NVDA", 3)]:
        df_raw = generate_synthetic(ticker, n_bars=756, trend="up", seed=seed)
        # Scala prezzi a livelli realistici (~150-400$)
        target = random.uniform(150, 400)
        ratio  = target / df_raw["close"].iloc[-1]
        for col in ["open", "high", "low", "close"]:
            df_raw[col] *= ratio

        print(f"  {ticker}...", end=" ", flush=True)
        # step=10 per velocità nel test (in produzione step=1)
        trades = backtest_ticker(ticker, df_raw,
                                 warmup=252, min_score=55,
                                 max_days=7, step=10,
                                 filters={**DEFAULT_FILTERS,
                                          "require_weekly_uptrend": False,
                                          "require_supertrend_bull": False,
                                          "require_adx_min": 15,
                                          "max_atr_pct": 5.0})
        all_trades.extend(trades)
        print(f"{len(trades)} trade")

    if all_trades:
        stats = compute_stats(all_trades, risk_per_trade_pct=1.0)
        print_report(stats)
    else:
        print("Nessun trade — abbassa min_score o usa dati reali con API key")
