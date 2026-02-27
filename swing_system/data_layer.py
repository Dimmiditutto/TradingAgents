"""
data_layer.py
─────────────
Gestisce il download e la cache dei dati OHLCV da Alpha Vantage.

ALPHA VANTAGE FREE:
  - 25 richieste API al giorno
  - Endpoint usati: TIME_SERIES_DAILY_ADJUSTED
  - Dati: daily OHLCV adjusted (gestisce split e dividendi)
  - History: fino a 20 anni (outputsize=full)

STRATEGIA CACHE:
  I dati sono salvati in CSV locali (data/cache/<TICKER>.csv).
  Ad ogni esecuzione:
    1. Carica il CSV esistente (se presente)
    2. Controlla se mancano barre recenti
    3. Scarica solo se necessario (usa 1 API call vs tutta la history)
  Questo permette di gestire 100 ticker con ~1-5 API call al giorno
  dopo il download iniziale.

FALLBACK CSV:
  Se non è disponibile una API key, carica dati da file CSV locali
  nella cartella data/manual/ con formato standard (Date,Open,High,Low,Close,Volume).
"""

import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAZIONE
# ──────────────────────────────────────────────────────────────────────────────

CACHE_DIR  = Path("data/cache")
MANUAL_DIR = Path("data/manual")
CONFIG_FILE = Path("config.json")

# Colonne standard dopo il download e la normalizzazione
OHLCV_COLS = ["open", "high", "low", "close", "volume"]


def load_config() -> dict:
    """Carica la configurazione da config.json o usa i default."""
    defaults = {
        "api_key": "demo",          # sostituire con la propria API key
        "cache_days": 1,            # giorni prima di considerare la cache obsoleta
        "rate_limit_sleep": 12,     # secondi tra chiamate API (25/giorno = 1/12s)
        "min_history_days": 252,    # minimo 1 anno di dati per il calcolo indicatori
        "full_output_threshold": 30 # giorni mancanti oltre i quali scarica full output
    }
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            user_cfg = json.load(f)
        defaults.update(user_cfg)
    return defaults


# ──────────────────────────────────────────────────────────────────────────────
# ALPHA VANTAGE CLIENT
# ──────────────────────────────────────────────────────────────────────────────

class AlphaVantageClient:
    """
    Client minimale per Alpha Vantage (zero dipendenze esterne).
    Usa solo urllib dalla libreria standard.
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str, sleep_between_calls: float = 12.0):
        self.api_key    = api_key
        self.sleep_secs = sleep_between_calls
        self._call_count = 0

    def _get(self, params: dict) -> dict:
        """Esegue una chiamata GET e ritorna il JSON."""
        params["apikey"] = self.api_key
        url = self.BASE_URL + "?" + urllib.parse.urlencode(params)

        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            raise ConnectionError(f"Alpha Vantage API error: {e}")

        if "Note" in data:
            raise RuntimeError(f"API rate limit reached: {data['Note']}")
        if "Error Message" in data:
            raise ValueError(f"API error: {data['Error Message']}")

        self._call_count += 1
        time.sleep(self.sleep_secs)   # rispetta il rate limit
        return data

    def get_daily(self, symbol: str, outputsize: str = "compact") -> pd.DataFrame:
        """
        Scarica dati daily adjusted.
        outputsize: "compact" (100 barre) o "full" (20 anni)
        """
        params = {
            "function":   "TIME_SERIES_DAILY_ADJUSTED",
            "symbol":     symbol,
            "outputsize": outputsize,
            "datatype":   "json",
        }
        raw = self._get(params)

        key = "Time Series (Daily)"
        if key not in raw:
            raise ValueError(f"Risposta inattesa per {symbol}: {list(raw.keys())}")

        ts = raw[key]
        records = []
        for date_str, vals in ts.items():
            records.append({
                "date":   date_str,
                "open":   float(vals.get("1. open", 0)),
                "high":   float(vals.get("2. high", 0)),
                "low":    float(vals.get("3. low", 0)),
                "close":  float(vals.get("5. adjusted close", vals.get("4. close", 0))),
                "volume": float(vals.get("6. volume", 0)),
            })

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        df.index.name = None
        return df


# ──────────────────────────────────────────────────────────────────────────────
# CACHE MANAGER
# ──────────────────────────────────────────────────────────────────────────────

class DataManager:
    """
    Gestisce il download, la cache e il caricamento dei dati OHLCV.

    Flusso per ogni ticker:
      1. Controlla se esiste la cache locale
      2. Se la cache è aggiornata (< cache_days giorni), la usa direttamente
      3. Se la cache è obsoleta o mancante, scarica i nuovi dati da API
      4. Aggiorna la cache e restituisce il DataFrame completo
    """

    def __init__(self, config: dict = None):
        self.cfg    = config or load_config()
        self.client = AlphaVantageClient(
            api_key             = self.cfg["api_key"],
            sleep_between_calls = self.cfg["rate_limit_sleep"],
        )
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        MANUAL_DIR.mkdir(parents=True, exist_ok=True)

    # ── Gestione cache

    def _cache_path(self, ticker: str) -> Path:
        return CACHE_DIR / f"{ticker.upper()}.csv"

    def _load_cache(self, ticker: str) -> Optional[pd.DataFrame]:
        path = self._cache_path(ticker)
        if not path.exists():
            return None
        try:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            df.columns = [c.lower() for c in df.columns]
            return df[OHLCV_COLS].dropna()
        except Exception:
            return None

    def _save_cache(self, ticker: str, df: pd.DataFrame) -> None:
        path = self._cache_path(ticker)
        df.to_csv(path)

    def _cache_is_fresh(self, df: pd.DataFrame) -> bool:
        """Cache fresca se l'ultima barra non è più vecchia di cache_days giorni lavorativi."""
        if df is None or df.empty:
            return False
        last_date  = df.index[-1]
        today      = pd.Timestamp.today().normalize()
        days_since = (today - last_date).days
        # Considera weekend: se oggi è lunedì e l'ultima barra è venerdì = 3 giorni
        return days_since <= self.cfg["cache_days"] * 3

    def _days_missing(self, df: pd.DataFrame) -> int:
        """Quanti giorni lavorativi mancano dalla cache ad oggi."""
        if df is None or df.empty:
            return 999
        last = df.index[-1]
        today = pd.Timestamp.today().normalize()
        return pd.bdate_range(last, today).size - 1

    # ── Caricamento da CSV manuale (fallback senza API)

    def load_manual_csv(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Carica dati da CSV in data/manual/<TICKER>.csv
        Formato atteso: Date,Open,High,Low,Close,Volume (header case-insensitive)
        """
        path = MANUAL_DIR / f"{ticker.upper()}.csv"
        if not path.exists():
            return None
        try:
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            df.columns = [c.lower() for c in df.columns]
            # Accetta anche 'adj close' come close
            if "adj close" in df.columns and "close" not in df.columns:
                df = df.rename(columns={"adj close": "close"})
            return df[OHLCV_COLS].dropna().sort_index()
        except Exception as e:
            print(f"[WARN] Impossibile caricare {path}: {e}")
            return None

    # ── Download con logica compact/full

    def _download(self, ticker: str, cached_df: Optional[pd.DataFrame]) -> pd.DataFrame:
        """
        Sceglie tra compact (100 barre) e full (20 anni) in base a quante barre mancano.
        """
        days_missing = self._days_missing(cached_df)
        threshold    = self.cfg.get("full_output_threshold", 30)

        if days_missing <= threshold:
            outputsize = "compact"
        else:
            outputsize = "full"

        print(f"  [API] {ticker}: download {outputsize} ({days_missing} giorni mancanti)")
        new_df = self.client.get_daily(ticker, outputsize)

        if cached_df is not None and not cached_df.empty:
            # Unisci con la cache (i nuovi dati hanno precedenza in caso di overlap)
            combined = pd.concat([cached_df, new_df])
            combined = combined[~combined.index.duplicated(keep="last")]
            return combined.sort_index()

        return new_df

    # ── Entry point principale

    def get(self, ticker: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
        """
        Restituisce il DataFrame OHLCV per un ticker.
        Gestisce automaticamente cache, download e fallback CSV.

        Args:
            ticker:        simbolo (es. "AAPL", "NVDA")
            force_refresh: ignora la cache e scarica sempre

        Returns:
            DataFrame OHLCV con DatetimeIndex, None se non disponibile
        """
        ticker = ticker.upper()

        # 1. Prova cache locale
        cached = self._load_cache(ticker)

        if not force_refresh and self._cache_is_fresh(cached):
            return cached

        # 2. Prova API (se non demo key o cache vuota)
        if self.cfg["api_key"] != "demo":
            try:
                df = self._download(ticker, cached)
                self._save_cache(ticker, df)
                return df
            except Exception as e:
                print(f"  [WARN] {ticker}: API error ({e}), uso cache/CSV")
                if cached is not None:
                    return cached

        # 3. Fallback CSV manuale
        manual = self.load_manual_csv(ticker)
        if manual is not None:
            return manual

        # 4. Usa cache anche se obsoleta (meglio di niente)
        if cached is not None:
            print(f"  [WARN] {ticker}: dati potenzialmente obsoleti (cache del {cached.index[-1].date()})")
            return cached

        print(f"  [ERROR] {ticker}: nessun dato disponibile")
        return None

    def get_many(self, tickers: list[str],
                 force_refresh: bool = False,
                 verbose: bool = True) -> dict[str, pd.DataFrame]:
        """
        Scarica dati per una lista di ticker con gestione del rate limit.
        Stampa un progress report durante il download.
        """
        results = {}
        n = len(tickers)

        for i, ticker in enumerate(tickers, 1):
            if verbose:
                print(f"[{i:3d}/{n}] {ticker:<8}", end=" ")

            df = self.get(ticker, force_refresh)

            if df is not None and len(df) >= self.cfg.get("min_history_days", 252):
                results[ticker] = df
                if verbose:
                    print(f"✓ {len(df)} barre  ({df.index[0].date()} → {df.index[-1].date()})")
            else:
                if verbose:
                    bars = len(df) if df is not None else 0
                    print(f"✗ dati insufficienti ({bars} barre)")

        return results


# ──────────────────────────────────────────────────────────────────────────────
# GENERATORE DATI SINTETICI (per test senza API)
# ──────────────────────────────────────────────────────────────────────────────

def generate_synthetic(ticker: str,
                        n_bars: int = 504,
                        trend: str = "up",
                        seed: int = 42) -> pd.DataFrame:
    """
    Genera dati OHLCV sintetici realistici per test.
    trend: "up", "down", "sideways", "volatile"
    Prezzi e volatilità calibrati su stock USA tipici (50-500$, ATR% 1-4%).
    """
    np.random.seed(hash(ticker + str(seed)) % 2**32)

    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n_bars)

    # Drift e volatilità annualizzata (parametri realistici per azioni USA)
    drift     = {"up": 0.25,  "down": -0.15, "sideways": 0.02,  "volatile": 0.10}[trend]
    annual_vol = {"up": 0.25, "down": 0.30,  "sideways": 0.18, "volatile": 0.45}[trend]

    daily_drift = drift / 252
    daily_vol   = annual_vol / np.sqrt(252)

    returns     = np.random.normal(daily_drift, daily_vol, n_bars)
    start_price = np.random.uniform(80, 400)   # prezzo iniziale realistico
    close       = start_price * np.cumprod(1 + returns)

    # Intraday range: 1.5-3% del prezzo (ATR% realistico per azioni S&P 500)
    intraday_pct = np.abs(np.random.normal(0.018, 0.006, n_bars)).clip(0.008, 0.045)
    half_range   = close * intraday_pct / 2

    high  = close + half_range * np.random.uniform(0.6, 1.4, n_bars)
    low   = close - half_range * np.random.uniform(0.6, 1.4, n_bars)
    low   = np.minimum(low, close)
    high  = np.maximum(high, close)
    open_ = np.roll(close, 1)
    open_[0] = close[0]

    base_vol = np.random.randint(2_000_000, 12_000_000)
    vol_mult = 1 + 3.0 * np.abs(returns) / daily_vol
    volume   = (base_vol * vol_mult * np.random.uniform(0.5, 1.5, n_bars)).astype(int).astype(float)

    return pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": volume
    }, index=dates)


# ──────────────────────────────────────────────────────────────────────────────
# WATCHLIST HELPER
# ──────────────────────────────────────────────────────────────────────────────

# S&P 500 subset: 60 titoli rappresentativi per settore
SP500_SUBSET = {
    "Technology":    ["AAPL", "MSFT", "NVDA", "META", "GOOGL", "AMZN", "TSLA", "AMD", "AVGO", "ORCL"],
    "Financials":    ["JPM", "BAC", "GS", "MS", "WFC", "BLK", "AXP", "SCHW", "USB", "PNC"],
    "Healthcare":    ["LLY", "UNH", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "AMGN"],
    "Industrials":   ["CAT", "BA", "HON", "UPS", "GE", "RTX", "DE", "MMM", "LMT", "FDX"],
    "ConsDiscretary":["HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "BKNG", "CMG", "YUM", "ROST"],
    "Energy":        ["XOM", "CVX", "COP", "EOG", "PXD", "SLB", "OXY", "PSX", "VLO", "MPC"],
}

def get_watchlist(sectors: list[str] = None) -> list[str]:
    """Restituisce la watchlist filtrata per settore."""
    if sectors is None:
        return [t for tickers in SP500_SUBSET.values() for t in tickers]
    return [t for s in sectors if s in SP500_SUBSET for t in SP500_SUBSET[s]]


# ──────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Test dati sintetici:")
    for trend in ["up", "down", "sideways"]:
        df = generate_synthetic("TEST", trend=trend)
        print(f"  {trend:10s}: {len(df)} barre, "
              f"close range [{df['close'].min():.1f} – {df['close'].max():.1f}]")

    print(f"\nWatchlist completa: {len(get_watchlist())} ticker")
    print(f"Solo Tech+Financials: {get_watchlist(['Technology','Financials'])}")
