"""
msft_swing_system.py
────────────────────
Sistema di swing trading su MSFT — Daily 1D.
Produce i risultati per 3 profili di rischio:
  • Conservativo : TF=1.0%, CP=0.5%,  MOM=1.0%
  • Bilanciato   : TF=1.8%, CP=0.9%,  MOM=1.8%   ← sweet spot
  • Aggressivo   : TF=2.5%, CP=1.25%, MOM=2.5%

Input richiesto
───────────────
File CSV OHLCV con colonne: time, open, high, low, close, volume
  • time: Unix timestamp (secondi) oppure stringa ISO date
  • Esempio: BATS_MSFT__1D.csv

Dipendenze
──────────
  pip install pandas numpy

Utilizzo
────────
  python msft_swing_system.py BATS_MSFT__1D.csv

Output
──────
  Stampa metriche complete per ogni profilo (n, WR, E[R], PF, CAGR,
  Sharpe, Sortino, MaxDD) calcolate su daily returns × √252.
  Sharpe/Sortino corretti: includono i giorni flat nella serie giornaliera.
"""

from __future__ import annotations
import sys
import numpy as np
import pandas as pd
from datetime import date, timedelta


# ═══════════════════════════════════════════════════════════════════════════════
#  SEZIONE 1 — INDICATORI TECNICI
#  Tutti i parametri sono qui, modificabili.
# ═══════════════════════════════════════════════════════════════════════════════

# ── Helper smoothing ──────────────────────────────────────────────────────────

def _ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()

def _sma(s: pd.Series, period: int) -> pd.Series:
    return s.rolling(window=period, min_periods=1).mean()

def _rma(s: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing — usato da ATR e ADX."""
    result = np.full(len(s), np.nan)
    vals = s.values
    alpha = 1.0 / period
    first = 0
    while first < len(vals) and np.isnan(vals[first]):
        first += 1
    if first >= len(vals):
        return pd.Series(result, index=s.index)
    result[first] = vals[first]
    for i in range(first + 1, len(vals)):
        if np.isnan(vals[i]):
            result[i] = result[i - 1]
        else:
            result[i] = alpha * vals[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=s.index)


def compute_indicators(
    df: pd.DataFrame,
    # ── Moving Averages ──────────────────────────────────────────────────────
    ema_period: int = 10,
    sma_fast: int = 50,
    sma_slow: int = 200,
    vwma_period: int = 20,
    # ── Momentum ─────────────────────────────────────────────────────────────
    rsi_period: int = 14,
    tsi_long: int = 13,       # più reattivo del default 25 — adatto swing 2-12g
    tsi_short: int = 7,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_sig: int = 9,
    # ── Volatilità ───────────────────────────────────────────────────────────
    bb_period: int = 20,
    bb_std: float = 2.0,
    atr_period: int = 14,
    # ── Forza trend ──────────────────────────────────────────────────────────
    adx_period: int = 14,
    er_period: int = 10,      # Efficiency Ratio (Kaufman)
    # ── Direzione trend ──────────────────────────────────────────────────────
    st_period: int = 10,      # SuperTrend
    st_multiplier: float = 3.0,
) -> pd.DataFrame:
    """
    Calcola tutti gli indicatori e restituisce il DataFrame arricchito.

    Indicatori calcolati:
      Moving Averages : EMA(10), SMA(50), SMA(200), VWMA(20)
      Momentum        : RSI(14), TSI(13/7)+signal, MACD(12/26/9)+hist+slope
      Volatilità      : Bollinger Bands(20,2) + bandwidth + %B, ATR(14)
      Forza trend     : ADX(14), +DI, −DI, Efficiency Ratio(10)
      Direzione trend : SuperTrend(10, 3.0)
    """
    df = df.copy()
    c = df["close"]
    h = df["high"]
    lo = df["low"]
    v = df["volume"]

    # ── Moving Averages ───────────────────────────────────────────────────────
    df["ema10"]        = _ema(c, ema_period)
    df["sma50"]        = _sma(c, sma_fast)
    df["sma200"]       = _sma(c, sma_slow)
    tp                 = (h + lo + c) / 3
    vol_sum            = v.rolling(vwma_period, min_periods=1).sum()
    df["vwma"]         = (tp * v).rolling(vwma_period, min_periods=1).sum() / vol_sum.replace(0, np.nan)
    df["pct_from_200"] = (c - df["sma200"]) / df["sma200"].replace(0, np.nan) * 100

    # ── RSI (Wilder) ──────────────────────────────────────────────────────────
    delta   = c.diff()
    gain    = delta.clip(lower=0)
    loss    = (-delta).clip(lower=0)
    df["rsi"] = 100 - (100 / (1 + _rma(gain, rsi_period) / _rma(loss, rsi_period).replace(0, np.nan)))

    # ── TSI (True Strength Index) — doppio EMA su price change ───────────────
    pc              = c.diff()
    apc             = pc.abs()
    df["tsi"]       = 100 * _ema(_ema(pc, tsi_long), tsi_short) / \
                      _ema(_ema(apc, tsi_long), tsi_short).replace(0, np.nan)
    df["tsi_signal"] = _ema(df["tsi"], tsi_short)

    # ── MACD ─────────────────────────────────────────────────────────────────
    df["macd"]       = _ema(c, macd_fast) - _ema(c, macd_slow)
    df["macd_sig"]   = _ema(df["macd"], macd_sig)
    df["macdh"]      = df["macd"] - df["macd_sig"]
    df["macdh_slope"] = df["macdh"].diff()   # derivata: accelerazione istogramma

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    bb_mid            = _sma(c, bb_period)
    bb_std_s          = c.rolling(bb_period, min_periods=1).std(ddof=0)
    df["bb_mid"]      = bb_mid
    df["bb_upper"]    = bb_mid + bb_std * bb_std_s
    df["bb_lower"]    = bb_mid - bb_std * bb_std_s
    bb_w              = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_bw"]       = bb_w / bb_mid.replace(0, np.nan) * 100   # bandwidth %
    df["bb_pctb"]     = (c - df["bb_lower"]) / bb_w              # %B [0..1]

    # ── ATR (Wilder) ──────────────────────────────────────────────────────────
    prev_c        = c.shift(1).fillna(c)
    tr            = pd.concat([h - lo, (h - prev_c).abs(), (lo - prev_c).abs()], axis=1).max(axis=1)
    df["atr"]     = _rma(tr, atr_period)
    df["atr_pct"] = df["atr"] / c * 100

    # ── ADX + DI ──────────────────────────────────────────────────────────────
    up        = h.diff().clip(lower=0)
    down      = (-lo.diff()).clip(lower=0)
    plus_dm   = up.where(up > down, 0)
    minus_dm  = down.where(down > up, 0)
    atr_adx   = _rma(tr, adx_period)
    plus_di   = 100 * _rma(plus_dm, adx_period) / atr_adx.replace(0, np.nan)
    minus_di  = 100 * _rma(minus_dm, adx_period) / atr_adx.replace(0, np.nan)
    dx        = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["plus_di"]  = plus_di
    df["minus_di"] = minus_di
    df["adx"]      = _rma(dx, adx_period)

    # ── Efficiency Ratio (Kaufman) ─────────────────────────────────────────────
    net       = (c - c.shift(er_period)).abs()
    path      = c.diff().abs().rolling(er_period, min_periods=1).sum()
    df["er"]  = (net / path.replace(0, np.nan)).clip(0, 1)

    # ── SuperTrend ────────────────────────────────────────────────────────────
    hl2           = (h + lo) / 2
    atr_st        = _rma(tr, st_period)
    upper_raw     = hl2 + st_multiplier * atr_st
    lower_raw     = hl2 - st_multiplier * atr_st

    n         = len(df)
    closes    = c.values
    ur        = upper_raw.values
    lr        = lower_raw.values
    upper     = np.zeros(n); lower = np.zeros(n)
    st_dir    = np.zeros(n, dtype=int)

    upper[0] = ur[0]; lower[0] = lr[0]; st_dir[0] = 1
    for i in range(1, n):
        upper[i] = ur[i] if ur[i] < upper[i-1] or closes[i-1] > upper[i-1] else upper[i-1]
        lower[i] = lr[i] if lr[i] > lower[i-1] or closes[i-1] < lower[i-1] else lower[i-1]
        if st_dir[i-1] == 1:
            st_dir[i] = 1 if closes[i] <= upper[i] else -1
        else:
            st_dir[i] = -1 if closes[i] >= lower[i] else 1

    df["st_dir"] = st_dir   # -1 = BULL (long allowed), +1 = BEAR

    return df.fillna(method="ffill")


# ═══════════════════════════════════════════════════════════════════════════════
#  SEZIONE 2 — MOTORE STRATEGIA
# ═══════════════════════════════════════════════════════════════════════════════

# ── Parametri segnali (ottimizzati su 13 anni walk-forward) ──────────────────
SIGNAL_PARAMS = {
    # Filtri comuni
    "mer"     : 0.22,   # ER minimo per Trend Following
    "madx"    : 10,     # ADX minimo (tutti i segnali)
    "mbw"     : 20,     # Bollinger Bandwidth massimo per CP (compressione)
    "merc"    : 0.16,   # ER minimo per Compression Breakout
    "rsi_mr"  : 40,     # RSI massimo per Mean Reversion
    "pb_mr"   : 0.35,   # Bollinger %B massimo per MR
    # Exit — LONG
    "sl"      : 1.2,    # Stop loss in ATR (TF/CP/MOM)
    "t1"      : 2.0,    # Target 1 in ATR → 50% exit → breakeven
    "t2"      : 4.0,    # Target 2 in ATR → trailing stop su 50% restante
    "trail"   : 1.5,    # Trailing stop dopo T1 (ATR sotto close)
    "max_hold": 12,     # Timeout in barre
    # Exit — MR (stop più stretto)
    "sl_mr"   : 1.0,
    "t1_mr"   : 1.6,
    "t2_mr"   : 3.2,
}

# ── 3 Profili di rischio ─────────────────────────────────────────────────────
#   risk/trade per segnale. CP sempre a metà del TF (in probation OOS).
#   MR sospeso (n=1 su 13 anni).

RISK_PROFILES = {
    "conservativo": {"TF": 1.00, "CP": 0.50, "MOM": 1.00, "MR": 0.0},
    "bilanciato":   {"TF": 1.80, "CP": 0.90, "MOM": 1.80, "MR": 0.0},
    "aggressivo":   {"TF": 2.50, "CP": 1.25, "MOM": 2.50, "MR": 0.0},
}

# Numero di barre di warmup prima del primo segnale
WARMUP = 252


def run_backtest(
    df: pd.DataFrame,
    params: dict,
    risk_map: dict,
    cost_r: float = 0.0,
    start_i: int | None = None,
    end_i: int | None = None,
) -> list[dict]:
    """
    Esegue il backtest walk-forward (no-lookahead) sulla finestra [start_i, end_i).

    Parametri
    ─────────
    df       : DataFrame con indicatori calcolati
    params   : SIGNAL_PARAMS
    risk_map : dizionario {segnale: risk%}
    cost_r   : costo round-trip in unità R (default 0)
    start_i  : indice barra di partenza (default WARMUP)
    end_i    : indice barra di fine (default len(df))

    Restituisce
    ───────────
    Lista di trade con: r, r_gross, type, risk, entry, exit, nb, close, year
    """
    C   = df["close"].values
    H   = df["high"].values
    L   = df["low"].values
    AT  = df["atr"].values
    IDX = df.index

    er_  = df["er"].fillna(0).values
    adx_ = df["adx"].fillna(0).values
    pdi_ = df["plus_di"].fillna(0).values
    mdi_ = df["minus_di"].fillna(0).values
    std_ = df["st_dir"].fillna(0).values.astype(int)
    bw_  = df["bb_bw"].fillna(10).values
    rsi_ = df["rsi"].fillna(50).values
    pb_  = df["bb_pctb"].fillna(0.5).values
    tsi_ = df["tsi"].fillna(0).values
    tss_ = df["tsi_signal"].fillna(0).values
    mhs_ = df["macdh_slope"].fillna(0).values
    s50_ = df["sma50"].fillna(0).values
    s200_= df["sma200"].fillna(0).values

    P   = params
    n   = len(df)
    si  = start_i if start_i is not None else WARMUP
    ei  = end_i   if end_i   is not None else n

    used   = set()
    trades = []

    for i in range(si, min(ei, n) - P["max_hold"] - 2):
        if i in used:
            continue

        er   = er_[i];  adx = adx_[i];  pdi = pdi_[i];  mdi = mdi_[i]
        st   = int(std_[i]); bw = bw_[i];   rsi = rsi_[i];  pb  = pb_[i]
        mhs  = mhs_[i];  atr = max(AT[i], 1e-5); entry = C[i]
        tsi_x = i > 0 and tsi_[i] > tss_[i] and tsi_[i-1] <= tss_[i-1]

        stype = None
        sl_u  = P["sl"];  t1_u = P["t1"];  t2_u = P["t2"]

        # ── Segnale TF — Trend Following ──────────────────────────────────────
        if er >= P["mer"] and adx >= P["madx"] and pdi > mdi and st == -1:
            stype = "TF"

        # ── Segnale CP — Compression Breakout ────────────────────────────────
        elif bw <= P["mbw"] and er >= P["merc"] and st == -1 and adx >= P["madx"] - 2:
            stype = "CP"

        # ── Segnale MOM — TSI Momentum Cross ─────────────────────────────────
        elif tsi_x and mhs > 0 and st == -1 and entry > s50_[i] and adx > 12:
            stype = "MOM"

        # ── Segnale MR — Mean Reversion (sospeso) ────────────────────────────
        elif rsi < P["rsi_mr"] and pb < P["pb_mr"] and entry > s200_[i] and st == -1:
            stype = "MR"
            sl_u  = P["sl_mr"];  t1_u = P["t1_mr"];  t2_u = P["t2_mr"]

        if stype is None or risk_map.get(stype, 0) == 0:
            continue

        risk_t = risk_map[stype]

        # ── Exit logic ────────────────────────────────────────────────────────
        stop_p = entry - sl_u  * atr
        tp1    = entry + t1_u  * atr
        tp2    = entry + t2_u  * atr

        r = None; part = False; trail_p = stop_p; nb = 0

        for d in range(1, P["max_hold"] + 1):
            ix = i + d
            if ix >= n:
                break
            hh = H[ix]; ll = L[ix]; cc = C[ix]; nb = d

            if ll <= trail_p:
                # Hit stop o trailing
                r = (t1_u * 0.5 + (trail_p - entry) / atr * 0.5) if part else -1.0
                break
            if hh >= tp2:
                # Target 2 raggiunto
                r = (t1_u * 0.5 + t2_u * 0.5) if part else t2_u
                break
            if hh >= tp1 and not part:
                # Target 1: uscita 50%, stop a breakeven
                part    = True
                trail_p = entry
            if part:
                # Trailing stop: max(entry, close − 1.5×ATR)
                trail_p = max(trail_p, cc - P["trail"] * AT[ix])

        if r is None:
            # Timeout: chiusura a close dell'ultima barra
            ep  = C[min(i + P["max_hold"], n - 1)]
            raw = (ep - entry) / atr
            r   = (t1_u * 0.5 + max(raw, 0) * 0.5) if part else raw

        r_net = r - cost_r  # sottrai costo round-trip in R

        for j in range(i, min(i + nb + 1, n)):
            used.add(j)

        trades.append({
            "r"       : float(r_net),
            "r_gross" : float(r),
            "type"    : stype,
            "risk"    : risk_t,
            "entry"   : str(IDX[i].date()),
            "exit"    : str(IDX[min(i + nb, n - 1)].date()),
            "nb"      : nb,
            "close"   : float(entry),
            "year"    : IDX[i].year,
            "atr_pct" : float(AT[i] / entry * 100),
        })

    return trades


# ═══════════════════════════════════════════════════════════════════════════════
#  SEZIONE 3 — STATISTICHE
# ═══════════════════════════════════════════════════════════════════════════════

def compute_stats(trades: list[dict]) -> dict | None:
    """
    Calcola metriche complete su daily returns (inclusi giorni flat).

    Sharpe e Sortino sono calcolati su daily returns × √252 — metodo corretto.
    Il calcolo per-trade esclude i giorni flat (~96%) e gonfia i valori.
    """
    if len(trades) < 5:
        return None

    rs   = np.array([t["r"] for t in trades])
    n    = len(rs)
    wr   = (rs > 0).mean() * 100
    er   = rs.mean()
    gp   = rs[rs > 0].sum()
    gl   = abs(rs[rs < 0].sum())
    pf   = gp / max(gl, 1e-9)

    # ── Equity curve su serie giornaliera (inclusi flat) ─────────────────────
    start_d = date.fromisoformat(trades[0]["entry"])
    end_d   = date.fromisoformat(trades[-1]["exit"])
    all_days: list[date] = []
    d = start_d
    while d <= end_d:
        all_days.append(d)
        d += timedelta(days=1)

    day_pnl: dict[date, float] = {}
    for t in trades:
        dt = date.fromisoformat(t["exit"])
        day_pnl[dt] = day_pnl.get(dt, 0.0) + t["r"] * t["risk"] / 100.0

    series = np.array([day_pnl.get(day, 0.0) for day in all_days])
    eq     = 100.0 * np.cumprod(1.0 + series)
    pk     = np.maximum.accumulate(eq)
    dd     = (eq - pk) / pk * 100.0
    mdd    = dd.min()
    yrs    = max(len(all_days) / 365.25, 0.01)
    cagr   = (eq[-1] / 100.0) ** (1.0 / yrs) * 100.0 - 100.0

    # ── Sharpe / Sortino (daily × √252) ──────────────────────────────────────
    mu      = series.mean()
    sigma   = series.std(ddof=1)
    neg     = series[series < 0]
    sigma_d = neg.std(ddof=1) if len(neg) > 1 else 1e-10
    ANN     = np.sqrt(252)
    sharpe  = mu / max(sigma,   1e-10) * ANN
    sortino = mu / max(sigma_d, 1e-10) * ANN

    # ── Breakdown per tipo segnale ────────────────────────────────────────────
    by: dict[str, dict] = {}
    for tp in sorted(set(t["type"] for t in trades)):
        sub  = [t["r"] for t in trades if t["type"] == tp]
        sr   = np.array(sub)
        gp_  = sr[sr > 0].sum()
        gl_  = abs(sr[sr < 0].sum())
        by[tp] = {
            "n"   : len(sr),
            "wr"  : round((sr > 0).mean() * 100, 1),
            "er"  : round(sr.mean(), 3),
            "pf"  : round(gp_ / max(gl_, 1e-9), 2),
            "risk": trades[[t["type"] for t in trades].index(tp)]["risk"],
        }

    return {
        "n"      : n,
        "wr"     : round(wr,     1),
        "er"     : round(er,     3),
        "pf"     : round(pf,     2),
        "cagr"   : round(cagr,   1),
        "sharpe" : round(sharpe, 3),
        "sortino": round(sortino,3),
        "mdd"    : round(mdd,    2),
        "yrs"    : round(yrs,    2),
        "freq"   : round(n / yrs,1),
        "by_type": by,
        "flat_pct": round((series == 0).mean() * 100, 1),
    }


def print_stats(profile_name: str, stats: dict) -> None:
    """Stampa le metriche in formato leggibile."""
    sep = "─" * 62
    print(f"\n{'═'*62}")
    print(f"  PROFILO: {profile_name.upper()}")
    print(sep)
    print(f"  Frequenza:  {stats['freq']:.1f} trade/anno  ({stats['n']} totali, {stats['yrs']:.1f} anni)")
    print(f"  Win Rate:   {stats['wr']:.1f}%")
    print(f"  E[R]:       {stats['er']:+.3f}R")
    print(f"  PF:         {stats['pf']:.2f}")
    print(f"  CAGR:       {stats['cagr']:+.1f}%")
    print(f"  Sharpe:     {stats['sharpe']:.3f}  (daily ×√252, {stats['flat_pct']:.0f}% giorni flat)")
    print(f"  Sortino:    {stats['sortino']:.3f}")
    print(f"  Max DD:     {stats['mdd']:.2f}%")
    print(sep)
    print(f"  Breakdown per segnale:")
    for tp, v in stats["by_type"].items():
        status = "✓" if v["pf"] >= 1.25 else ("⚠" if v["pf"] >= 1.0 else "✗")
        print(f"    {status} {tp:<6}  n={v['n']:3d}  WR={v['wr']:5.1f}%  "
              f"E[R]={v['er']:+.3f}  PF={v['pf']:.2f}  risk={v['risk']:.3f}%")
    print(f"{'═'*62}")


# ═══════════════════════════════════════════════════════════════════════════════
#  SEZIONE 4 — ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def load_csv(path: str) -> pd.DataFrame:
    """
    Carica un CSV OHLCV.
    Accetta 'time' come Unix timestamp (secondi) o stringa ISO date.
    """
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]

    # Converti time
    if df["time"].dtype in (np.int64, np.float64):
        df["time"] = pd.to_datetime(df["time"], unit="s")
    else:
        df["time"] = pd.to_datetime(df["time"])

    df = df.set_index("time")
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    return df


def main(csv_path: str, cost_eur_rt: float = 20.0, capital_eur: float = 25_000.0):
    """
    Punto di ingresso principale.

    Parametri
    ─────────
    csv_path      : percorso al file CSV OHLCV
    cost_eur_rt   : costo round-trip in EUR (default €20 = €10 × 2 lati)
    capital_eur   : capitale base in EUR per calcolo del costo in R
    """
    print(f"Caricamento dati: {csv_path}")
    df_raw = load_csv(csv_path)
    print(f"  Barre caricate: {len(df_raw)}  ({df_raw.index[0].date()} → {df_raw.index[-1].date()})")

    print("Calcolo indicatori...")
    df = compute_indicators(df_raw)

    print(f"\nParametri segnali: {SIGNAL_PARAMS}")

    for profile_name, risk_map in RISK_PROFILES.items():
        # Calcola costo round-trip in R per il profilo (usa risk TF come riferimento)
        one_R_eur = capital_eur * risk_map["TF"] / 100.0
        cost_r    = cost_eur_rt / one_R_eur

        trades = run_backtest(
            df         = df,
            params     = SIGNAL_PARAMS,
            risk_map   = risk_map,
            cost_r     = cost_r,
            start_i    = WARMUP,
        )

        stats = compute_stats(trades)
        if stats is None:
            print(f"\n[{profile_name}] Troppo pochi trade ({len(trades)}) — dati insufficienti.")
            continue

        stats["cost_r"] = round(cost_r, 5)
        print_stats(profile_name, stats)

    print("\nNote:")
    print(f"  • Costo simulato: €{cost_eur_rt:.0f} round-trip su cap. €{capital_eur:,.0f}")
    print(f"  • Sharpe/Sortino: daily returns × √252 (inclusi giorni flat)")
    print(f"  • MR sospeso: n=1 su 13 anni — riattivare con N≥30 OOS")
    print(f"  • Bear 2022: unico fallimento strutturale (long-only system)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizzo: python msft_swing_system.py <path_csv>")
        print("Esempio:  python msft_swing_system.py BATS_MSFT__1D.csv")
        print("\nOpzionale: aggiungere costo RT e capitale")
        print("Esempio:  python msft_swing_system.py BATS_MSFT__1D.csv 20 25000")
        sys.exit(1)

    csv_file = sys.argv[1]
    cost_rt  = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
    capital  = float(sys.argv[3]) if len(sys.argv) > 3 else 25_000.0

    main(csv_file, cost_rt, capital)
