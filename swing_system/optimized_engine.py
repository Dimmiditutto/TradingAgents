"""
optimized_engine.py
Parameterized swing engine based on msft_swing_system.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_INDICATOR_PARAMS = {
    "ema_period": 10,
    "sma_fast": 50,
    "sma_slow": 200,
    "vwma_period": 20,
    "rsi_period": 14,
    "tsi_long": 13,
    "tsi_short": 7,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_sig": 9,
    "bb_period": 20,
    "bb_std": 2.0,
    "atr_period": 14,
    "adx_period": 14,
    "er_period": 10,
    "st_period": 10,
    "st_multiplier": 3.0,
}

DEFAULT_SIGNAL_PARAMS = {
    "mer": 0.22,
    "madx": 10,
    "mbw": 20,
    "merc": 0.16,
    "rsi_mr": 40,
    "pb_mr": 0.35,
    "sl": 1.2,
    "t1": 2.0,
    "t2": 4.0,
    "trail": 1.5,
    "max_hold": 12,
    "sl_mr": 1.0,
    "t1_mr": 1.6,
    "t2_mr": 3.2,
}

DEFAULT_RISK_PROFILES = {
    "conservativo": {"TF": 1.00, "CP": 0.50, "MOM": 1.00, "MR": 0.0},
    "bilanciato": {"TF": 1.80, "CP": 0.90, "MOM": 1.80, "MR": 0.0},
    "aggressivo": {"TF": 2.50, "CP": 1.25, "MOM": 2.50, "MR": 0.0},
}

DEFAULT_SIGNAL_SCORES = {
    "TF": 80.0,
    "CP": 70.0,
    "MOM": 75.0,
    "MR": 60.0,
}

DEFAULT_WARMUP = 252


def _merge_dict(base: dict, override: dict | None) -> dict:
    if not override:
        return dict(base)
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _merge_dict(merged[k], v)
        else:
            merged[k] = v
    return merged


def _parse_value(raw: str) -> object:
    v = raw.strip()
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def _load_csv_params(path: Path) -> dict:
    import csv

    out: dict = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            section = (row.get("section") or "").strip()
            key = (row.get("key") or "").strip()
            value = _parse_value(row.get("value") or "")
            if not section or not key:
                continue
            if section == "meta":
                out[key] = value
            elif section == "risk_profiles" and "." in key:
                prof, pkey = key.split(".", 1)
                out.setdefault(section, {}).setdefault(prof, {})[pkey] = value
            else:
                out.setdefault(section, {})[key] = value
    return out


def load_ticker_params(ticker: str, params_dir: str | None) -> dict:
    params = {
        "indicators": dict(DEFAULT_INDICATOR_PARAMS),
        "signals": dict(DEFAULT_SIGNAL_PARAMS),
        "risk_profiles": dict(DEFAULT_RISK_PROFILES),
        "signal_scores": dict(DEFAULT_SIGNAL_SCORES),
        "warmup": DEFAULT_WARMUP,
        "risk_profile_default": "bilanciato",
    }
    if not params_dir:
        return params

    path = Path(params_dir) / f"{ticker.upper()}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        csv_path = Path(params_dir) / f"{ticker.upper()}.csv"
        if not csv_path.exists():
            return params
        data = _load_csv_params(csv_path)
    for key in ("indicators", "signals", "risk_profiles", "signal_scores"):
        params[key] = _merge_dict(params[key], data.get(key, {}))
    if "warmup" in data:
        params["warmup"] = int(data["warmup"])
    if "risk_profile_default" in data:
        params["risk_profile_default"] = data["risk_profile_default"]
    return params


def _ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def _sma(s: pd.Series, period: int) -> pd.Series:
    return s.rolling(window=period, min_periods=1).mean()


def _rma(s: pd.Series, period: int) -> pd.Series:
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


def compute_indicators(df: pd.DataFrame, params: dict | None = None) -> pd.DataFrame:
    p = _merge_dict(DEFAULT_INDICATOR_PARAMS, params or {})
    df = df.copy()
    c = df["close"]
    h = df["high"]
    lo = df["low"]
    v = df["volume"]

    df["ema10"] = _ema(c, p["ema_period"])
    df["sma50"] = _sma(c, p["sma_fast"])
    df["sma200"] = _sma(c, p["sma_slow"])
    tp = (h + lo + c) / 3
    vol_sum = v.rolling(p["vwma_period"], min_periods=1).sum()
    df["vwma"] = (tp * v).rolling(p["vwma_period"], min_periods=1).sum() / vol_sum.replace(0, np.nan)
    df["pct_from_200"] = (c - df["sma200"]) / df["sma200"].replace(0, np.nan) * 100

    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    df["rsi"] = 100 - (100 / (1 + _rma(gain, p["rsi_period"]) / _rma(loss, p["rsi_period"]).replace(0, np.nan)))

    pc = c.diff()
    apc = pc.abs()
    df["tsi"] = 100 * _ema(_ema(pc, p["tsi_long"]), p["tsi_short"]) / _ema(
        _ema(apc, p["tsi_long"]), p["tsi_short"]
    ).replace(0, np.nan)
    df["tsi_signal"] = _ema(df["tsi"], p["tsi_short"])

    df["macd"] = _ema(c, p["macd_fast"]) - _ema(c, p["macd_slow"])
    df["macd_sig"] = _ema(df["macd"], p["macd_sig"])
    df["macdh"] = df["macd"] - df["macd_sig"]
    df["macdh_slope"] = df["macdh"].diff()

    bb_mid = _sma(c, p["bb_period"])
    bb_std_s = c.rolling(p["bb_period"], min_periods=1).std(ddof=0)
    df["bb_mid"] = bb_mid
    df["bb_upper"] = bb_mid + p["bb_std"] * bb_std_s
    df["bb_lower"] = bb_mid - p["bb_std"] * bb_std_s
    bb_w = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_bw"] = bb_w / bb_mid.replace(0, np.nan) * 100
    df["bb_pctb"] = (c - df["bb_lower"]) / bb_w

    prev_c = c.shift(1).fillna(c)
    tr = pd.concat([h - lo, (h - prev_c).abs(), (lo - prev_c).abs()], axis=1).max(axis=1)
    df["atr"] = _rma(tr, p["atr_period"])
    df["atr_pct"] = df["atr"] / c * 100

    up = h.diff().clip(lower=0)
    down = (-lo.diff()).clip(lower=0)
    plus_dm = up.where(up > down, 0)
    minus_dm = down.where(down > up, 0)
    atr_adx = _rma(tr, p["adx_period"])
    plus_di = 100 * _rma(plus_dm, p["adx_period"]) / atr_adx.replace(0, np.nan)
    minus_di = 100 * _rma(minus_dm, p["adx_period"]) / atr_adx.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di
    df["adx"] = _rma(dx, p["adx_period"])

    net = (c - c.shift(p["er_period"])).abs()
    path = c.diff().abs().rolling(p["er_period"], min_periods=1).sum()
    df["er"] = (net / path.replace(0, np.nan)).clip(0, 1)

    hl2 = (h + lo) / 2
    atr_st = _rma(tr, p["st_period"])
    upper_raw = hl2 + p["st_multiplier"] * atr_st
    lower_raw = hl2 - p["st_multiplier"] * atr_st

    n = len(df)
    closes = c.values
    ur = upper_raw.values
    lr = lower_raw.values
    upper = np.zeros(n)
    lower = np.zeros(n)
    st_dir = np.zeros(n, dtype=int)

    upper[0] = ur[0]
    lower[0] = lr[0]
    st_dir[0] = 1
    for i in range(1, n):
        upper[i] = ur[i] if ur[i] < upper[i - 1] or closes[i - 1] > upper[i - 1] else upper[i - 1]
        lower[i] = lr[i] if lr[i] > lower[i - 1] or closes[i - 1] < lower[i - 1] else lower[i - 1]
        if st_dir[i - 1] == 1:
            st_dir[i] = 1 if closes[i] <= upper[i] else -1
        else:
            st_dir[i] = -1 if closes[i] >= lower[i] else 1

    df["st_dir"] = st_dir

    return df.ffill()


@dataclass
class SignalResult:
    ticker: str
    timestamp: pd.Timestamp
    signal_type: str
    entry_price: float
    stop_loss: float
    target1: float
    target2: float
    atr_pct: float
    adx: float
    rsi: float
    risk_reward: float
    score: float

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "timestamp": str(self.timestamp),
            "direction": "LONG",
            "score": self.score,
            "filters_passed": True,
            "filter_failures": [],
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target1": self.target1,
            "target2": self.target2,
            "risk_reward": self.risk_reward,
            "atr_pct": self.atr_pct,
            "weekly_trend": "",
            "daily_trend": "",
            "structure_event": self.signal_type,
            "adx": self.adx,
            "rsi": self.rsi,
            "volume_ratio": None,
        }


def _detect_signal_type(df: pd.DataFrame, i: int, params: dict) -> str | None:
    er = float(df["er"].iloc[i])
    adx = float(df["adx"].iloc[i])
    pdi = float(df["plus_di"].iloc[i])
    mdi = float(df["minus_di"].iloc[i])
    st = int(df["st_dir"].iloc[i])
    bw = float(df["bb_bw"].iloc[i])
    rsi = float(df["rsi"].iloc[i])
    pb = float(df["bb_pctb"].iloc[i])
    tsi = float(df["tsi"].iloc[i])
    tss = float(df["tsi_signal"].iloc[i])
    mhs = float(df["macdh_slope"].iloc[i])
    s50 = float(df["sma50"].iloc[i])
    entry = float(df["close"].iloc[i])

    tsi_x = i > 0 and tsi > tss and df["tsi"].iloc[i - 1] <= df["tsi_signal"].iloc[i - 1]

    if er >= params["mer"] and adx >= params["madx"] and pdi > mdi and st == -1:
        return "TF"
    if bw <= params["mbw"] and er >= params["merc"] and st == -1 and adx >= params["madx"] - 2:
        return "CP"
    if tsi_x and mhs > 0 and st == -1 and entry > s50 and adx > 12:
        return "MOM"
    if rsi < params["rsi_mr"] and pb < params["pb_mr"] and entry > df["sma200"].iloc[i] and st == -1:
        return "MR"
    return None


def _signal_levels(entry: float, atr: float, signal_type: str, params: dict) -> tuple[float, float, float]:
    if signal_type == "MR":
        sl_u = params["sl_mr"]
        t1_u = params["t1_mr"]
        t2_u = params["t2_mr"]
    else:
        sl_u = params["sl"]
        t1_u = params["t1"]
        t2_u = params["t2"]

    stop_p = entry - sl_u * atr
    tp1 = entry + t1_u * atr
    tp2 = entry + t2_u * atr
    return stop_p, tp1, tp2


def scan_ticker(
    ticker: str,
    df_raw: pd.DataFrame,
    params: dict,
    min_score: float,
    risk_profile: str,
) -> list[dict]:
    if df_raw is None or len(df_raw) < params.get("warmup", DEFAULT_WARMUP):
        return []

    df = compute_indicators(df_raw, params.get("indicators"))
    i = len(df) - 1
    if i < params.get("warmup", DEFAULT_WARMUP):
        return []

    stype = _detect_signal_type(df, i, params.get("signals", DEFAULT_SIGNAL_PARAMS))
    if not stype:
        return []

    score = float(params.get("signal_scores", DEFAULT_SIGNAL_SCORES).get(stype, 0.0))
    if score < min_score:
        return []

    risk_profiles = params.get("risk_profiles", DEFAULT_RISK_PROFILES)
    risk_map = risk_profiles.get(risk_profile, risk_profiles.get(params.get("risk_profile_default", "bilanciato"), {}))
    if risk_map.get(stype, 0) <= 0:
        return []

    entry = float(df["close"].iloc[i])
    atr = max(float(df["atr"].iloc[i]), 1e-8)
    stop_p, tp1, tp2 = _signal_levels(entry, atr, stype, params.get("signals", DEFAULT_SIGNAL_PARAMS))
    rr = (tp1 - entry) / max(entry - stop_p, 1e-8)

    sig = SignalResult(
        ticker=ticker,
        timestamp=df.index[i],
        signal_type=stype,
        entry_price=entry,
        stop_loss=stop_p,
        target1=tp1,
        target2=tp2,
        atr_pct=float(df["atr_pct"].iloc[i]),
        adx=float(df["adx"].iloc[i]),
        rsi=float(df["rsi"].iloc[i]),
        risk_reward=float(rr),
        score=score,
    )
    return [sig.to_dict()]


def run_backtest(
    df: pd.DataFrame,
    params: dict,
    risk_map: dict,
    cost_r: float = 0.0,
    start_i: int | None = None,
    end_i: int | None = None,
    signal_scores: dict | None = None,
) -> list[dict]:
    c = df["close"].values
    h = df["high"].values
    l = df["low"].values
    at = df["atr"].values
    idx = df.index

    n = len(df)
    si = start_i if start_i is not None else DEFAULT_WARMUP
    ei = end_i if end_i is not None else n

    used = set()
    trades: list[dict] = []

    scores_map = signal_scores or DEFAULT_SIGNAL_SCORES

    for i in range(si, min(ei, n) - params["max_hold"] - 2):
        if i in used:
            continue

        stype = _detect_signal_type(df, i, params)
        if not stype or risk_map.get(stype, 0) == 0:
            continue

        entry = float(c[i])
        atr = max(float(at[i]), 1e-5)
        stop_p, tp1, tp2 = _signal_levels(entry, atr, stype, params)
        t1_u = params["t1_mr"] if stype == "MR" else params["t1"]
        t2_u = params["t2_mr"] if stype == "MR" else params["t2"]

        r = None
        part = False
        trail_p = stop_p
        nb = 0

        for d in range(1, params["max_hold"] + 1):
            ix = i + d
            if ix >= n:
                break
            hh = h[ix]
            ll = l[ix]
            cc = c[ix]
            nb = d

            if ll <= trail_p:
                r = (t1_u * 0.5 + (trail_p - entry) / atr * 0.5) if part else -1.0
                exit_reason = "STOP" if not part else "TRAIL"
                break
            if hh >= tp2:
                r = (t1_u * 0.5 + t2_u * 0.5) if part else t2_u
                exit_reason = "T2"
                break
            if hh >= tp1 and not part:
                part = True
                trail_p = entry
            if part:
                trail_p = max(trail_p, cc - params["trail"] * at[ix])

        if r is None:
            ep = c[min(i + params["max_hold"], n - 1)]
            raw = (ep - entry) / atr
            r = (t1_u * 0.5 + max(raw, 0) * 0.5) if part else raw
            exit_reason = "TIMEOUT"

        r_net = r - cost_r

        for j in range(i, min(i + nb + 1, n)):
            used.add(j)

        trades.append({
            "ticker": "",
            "direction": "LONG",
            "type": stype,
            "score": float(scores_map.get(stype, 0.0)),
            "risk": float(risk_map.get(stype, 0.0)),
            "entry": str(idx[i].date()),
            "exit": str(idx[min(i + nb, n - 1)].date()),
            "nb": int(nb),
            "close": float(entry),
            "year": int(idx[i].year),
            "atr_pct": float(at[i] / entry * 100),
            "r": float(r_net),
            "r_gross": float(r),
            "exit_reason": exit_reason,
        })

    return trades


def backtest_ticker(
    ticker: str,
    df_raw: pd.DataFrame,
    params: dict,
    risk_profile: str,
    cost_r: float = 0.0,
) -> list[dict]:
    df = compute_indicators(df_raw, params.get("indicators"))
    risk_profiles = params.get("risk_profiles", DEFAULT_RISK_PROFILES)
    risk_map = risk_profiles.get(risk_profile, risk_profiles.get(params.get("risk_profile_default", "bilanciato"), {}))
    warmup = params.get("warmup", DEFAULT_WARMUP)
    trades = run_backtest(
        df,
        params.get("signals", DEFAULT_SIGNAL_PARAMS),
        risk_map,
        cost_r=cost_r,
        start_i=warmup,
        signal_scores=params.get("signal_scores", DEFAULT_SIGNAL_SCORES),
    )
    for t in trades:
        t["ticker"] = ticker
    return trades


def _breakdown(df: pd.DataFrame, group_col: str) -> dict:
    g = df.groupby(group_col)
    res = {}
    for name, grp in g:
        n_g = len(grp)
        wr_g = grp["won"].mean() * 100 if n_g else 0.0
        pnl_g = grp["pnl_r"].sum()
        rr_g = grp["r"].mean() if n_g else 0.0
        res[str(name)] = {
            "count": n_g,
            "win_rate": round(float(wr_g), 1),
            "total_pnl_r": round(float(pnl_g), 2),
            "avg_rr": round(float(rr_g), 2),
        }
    return res


def compute_stats(trades: list[dict], risk_per_trade_pct: float | None = None) -> dict:
    if not trades:
        return {"error": "Nessun trade"}

    df = pd.DataFrame(trades)
    df["entry_date"] = pd.to_datetime(df["entry"], errors="coerce")
    df["exit_date"] = pd.to_datetime(df["exit"], errors="coerce")
    df = df.sort_values("exit_date").reset_index(drop=True)

    df["risk_pct"] = df["risk"].fillna(0.0)
    df["pnl_r"] = df["r"] * df["risk_pct"]
    df["won"] = df["r"] > 0

    n = len(df)
    n_won = int(df["won"].sum())
    wr = n_won / n * 100

    gross_p = df["pnl_r"][df["pnl_r"] > 0].sum()
    gross_l = df["pnl_r"][df["pnl_r"] < 0].abs().sum()
    pf = gross_p / max(gross_l, 1e-10)

    equity = [100.0]
    for pnl in df["pnl_r"]:
        equity.append(equity[-1] * (1 + pnl / 100))
    equity = np.array(equity[1:])

    total_return = (equity[-1] - 100) / 100 * 100

    first_date = df["entry_date"].iloc[0]
    last_date = df["exit_date"].iloc[-1]
    years = max((last_date - first_date).days / 365.25, 0.01)
    cagr = ((equity[-1] / 100) ** (1 / years) - 1) * 100

    peak = np.maximum.accumulate(equity)
    dd_pct = (equity - peak) / peak * 100
    max_dd = float(dd_pct.min())
    avg_dd = float(dd_pct[dd_pct < 0].mean()) if (dd_pct < 0).any() else 0.0

    daily_ret = pd.Series(df["pnl_r"].values)
    sharpe = (daily_ret.mean() / max(daily_ret.std(), 1e-10)) * np.sqrt(252)

    neg = daily_ret[daily_ret < 0]
    down_dev = neg.std() if len(neg) > 1 else 1e-10
    sortino = (daily_ret.mean() / max(down_dev, 1e-10)) * np.sqrt(252)

    avg_rr = float(df["r"].mean())
    avg_hold = float(df["nb"].mean()) if "nb" in df.columns else 0.0

    equity_series = [
        {"date": str(d.date()), "equity": round(float(e), 4)}
        for d, e in zip(df["exit_date"], equity)
        if pd.notna(d)
    ]

    df["score_clean"] = df["score"].fillna(0)
    df["score_bucket"] = (
        ((df["score_clean"] // 10) * 10).astype(int).astype(str)
        + "-"
        + ((df["score_clean"] // 10) * 10 + 9).astype(int).astype(str)
    )

    def dur_bucket(n_bars: float) -> str:
        if n_bars <= 3:
            return "1-3g"
        if n_bars <= 7:
            return "4-7g"
        return "8+g"

    df["dur_bucket"] = df["nb"].fillna(0).apply(dur_bucket)

    risk_per_trade = float(risk_per_trade_pct) if risk_per_trade_pct is not None else float(df["risk_pct"].mean())

    return {
        "summary": {
            "total_trades": n,
            "n_won": n_won,
            "win_rate_pct": round(wr, 1),
            "profit_factor": round(pf, 2),
            "avg_rr": round(avg_rr, 2),
            "total_pnl_pct": round(total_return, 2),
            "cagr_pct": round(cagr, 2),
            "sharpe": round(sharpe, 2),
            "sortino": round(sortino, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "avg_drawdown_pct": round(avg_dd, 2),
            "avg_hold_days": round(avg_hold, 1),
            "gross_profit_r": round(gross_p, 2),
            "gross_loss_r": round(gross_l, 2),
            "years_tested": round(years, 1),
            "risk_per_trade": round(risk_per_trade, 2),
        },
        "equity_series": equity_series,
        "by_event": _breakdown(df, "type"),
        "by_direction": _breakdown(df, "direction"),
        "by_score_bucket": _breakdown(df, "score_bucket"),
        "by_duration": _breakdown(df, "dur_bucket"),
        "by_exit_reason": _breakdown(df, "exit_reason"),
        "trades_sample": df.head(200).to_dict("records"),
    }
