"""
screener.py  —  MTF Swing System
Runner principale. Uso:
  python screener.py scan        [--synthetic] [--score 65]
  python screener.py backtest    [--synthetic] [--tickers 10]
  python screener.py dashboard
"""
import argparse, csv, json, sys, webbrowser
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from indicators      import compute_all
from market_structure import analyze as analyze_structure
from scoring         import score_both_directions, DEFAULT_FILTERS, DEFAULT_WEIGHTS, DEFAULT_TRADE
from data_layer      import DataManager, load_config, generate_synthetic, SP500_SUBSET
from backtest        import backtest_ticker, compute_stats, print_report, Trade, simulate_trade
from dashboard       import generate_dashboard

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ── scan ─────────────────────────────────────────────────────────────────────

def run_scan(cfg, synthetic=False):
    tickers   = cfg.get("watchlist") or cfg.get("tickers") or \
                [t for ts in SP500_SUBSET.values() for t in ts]
    min_score = cfg.get("min_score", 65.0)
    dm        = DataManager(cfg)
    signals   = []

    print(f"\n{'═'*58}")
    print(f"  MTF SWING SCAN — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Ticker: {len(tickers)}  Score soglia: {min_score}")
    print(f"{'═'*58}\n")

    for i, tk in enumerate(tickers, 1):
        print(f"[{i:3d}/{len(tickers)}] {tk:<7}", end=" ", flush=True)
        try:
            if synthetic:
                df_raw = generate_synthetic(tk, n_bars=504, trend="up", seed=i)
                ratio  = np.random.uniform(80, 500) / df_raw["close"].iloc[-1]
                for c in ["open","high","low","close"]: df_raw[c] *= ratio
            else:
                df_raw = dm.get(tk)
            if df_raw is None or len(df_raw) < 252:
                print("✗ dati insufficienti"); continue

            df      = compute_all(df_raw)
            result  = analyze_structure(df, include_weekly=True)
            mtf     = result.get("mtf", {})
            if not mtf:
                print("✗ MTF non disponibile"); continue

            sigs = score_both_directions(
                tk, df, mtf,
                weights=cfg.get("weights", DEFAULT_WEIGHTS),
                filters=cfg.get("filters", DEFAULT_FILTERS),
                trade_params=cfg.get("trade", DEFAULT_TRADE),
                min_score=min_score,
            )
            if sigs:
                for s in sigs: signals.append(s.to_dict())
                best = max(sigs, key=lambda s: s.score)
                ic   = "🟢" if best.direction == "LONG" else "🔴"
                print(f"{ic} {best.direction:<5} score={best.score:.0f}  "
                      f"ADX={best.adx:.0f}  RSI={best.rsi:.0f}  "
                      f"RR={best.risk_reward:.2f}  [{best.structure_event or '—'}]")
            else:
                print("—")
        except Exception as e:
            print(f"✗ {e}")

    signals.sort(key=lambda s: s["score"], reverse=True)

    if signals:
        ts  = datetime.now().strftime("%Y%m%d_%H%M")
        out = OUTPUT_DIR / f"scan_{ts}.csv"
        with open(out, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=signals[0].keys()).writeheader()
            csv.DictWriter(f, fieldnames=signals[0].keys()).writerows(signals)
        print(f"\n✓ {len(signals)} segnali → {out}")

    print(f"\n{'─'*58}  TOP SEGNALI")
    for s in signals[:10]:
        ic = "▲" if s["direction"]=="LONG" else "▼"
        print(f"  {ic} {s['ticker']:<6} {s['direction']:<5} "
              f"score={s['score']:>5.1f}  entry={s['entry_price']:>8.2f}  "
              f"stop={s['stop_loss']:>8.2f}  T1={s['target1']:>8.2f}  "
              f"RR={s['risk_reward']:.2f}  [{s['structure_event'] or '—'}]")
    return signals


# ── backtest ──────────────────────────────────────────────────────────────────

def run_backtest(cfg, n_tickers=10, synthetic=False):
    tickers    = (cfg.get("watchlist") or
                  [t for ts in SP500_SUBSET.values() for t in ts])[:n_tickers]
    dm         = DataManager(cfg)
    all_trades = []
    filters    = {**DEFAULT_FILTERS,
                  "require_weekly_uptrend":  False,
                  "require_supertrend_bull": False,
                  "require_adx_min": 15,
                  "max_atr_pct": 6.0}

    print(f"\n{'═'*58}")
    print(f"  BACKTEST — {len(tickers)} ticker")
    print(f"{'═'*58}\n")

    for tk in tickers:
        print(f"  {tk}...", end=" ", flush=True)
        if synthetic:
            df_raw = generate_synthetic(tk, n_bars=756, trend="up")
            ratio  = np.random.uniform(80, 400) / df_raw["close"].iloc[-1]
            for c in ["open","high","low","close"]: df_raw[c] *= ratio
        else:
            df_raw = dm.get(tk)
        if df_raw is None or len(df_raw) < 300:
            print("✗"); continue

        trades = backtest_ticker(tk, df_raw,
                                 warmup=252, min_score=cfg.get("min_score",60),
                                 max_days=cfg.get("max_hold_days",7),
                                 step=5, filters=filters)
        all_trades.extend(trades)
        print(f"✓ {len(trades)} trade")

    if not all_trades:
        print("\nNessun trade — abbassa min_score o usa --synthetic")
        return {}

    stats = compute_stats(all_trades, risk_per_trade_pct=cfg.get("risk_per_trade",1.0))
    print_report(stats)

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    (OUTPUT_DIR / f"bt_stats_{ts}.json").write_text(
        json.dumps(stats, indent=2, default=str), encoding="utf-8")
    print(f"\n✓ Stats → output/bt_stats_{ts}.json")
    return stats


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="MTF Swing Screener")
    ap.add_argument("command", choices=["scan","backtest","dashboard"])
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--tickers",   type=int, default=10)
    ap.add_argument("--score",     type=float, default=60.0)
    args = ap.parse_args()

    cfg = load_config()
    cfg["min_score"] = args.score

    bt_stats = None

    if args.command == "scan":
        signals  = run_scan(cfg, synthetic=args.synthetic)
        path     = generate_dashboard(signals, bt_stats=None)

    elif args.command == "backtest":
        # Carica l'ultimo scan se disponibile
        scans   = sorted(OUTPUT_DIR.glob("scan_*.csv"), reverse=True)
        signals = pd.read_csv(scans[0]).to_dict("records") if scans else []
        bt_stats = run_backtest(cfg, n_tickers=args.tickers, synthetic=args.synthetic)
        path    = generate_dashboard(signals, bt_stats=bt_stats)

    elif args.command == "dashboard":
        scans   = sorted(OUTPUT_DIR.glob("scan_*.csv"), reverse=True)
        signals = pd.read_csv(scans[0]).to_dict("records") if scans else []
        bts     = sorted(OUTPUT_DIR.glob("bt_stats_*.json"), reverse=True)
        bt_stats = json.loads(bts[0].read_text()) if bts else None
        path    = generate_dashboard(signals, bt_stats=bt_stats)

    print(f"\n✓ Dashboard → {path}")
    try: webbrowser.open(f"file://{path.absolute()}")
    except: pass


if __name__ == "__main__":
    main()
