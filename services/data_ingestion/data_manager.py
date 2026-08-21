# ============================================================
# data_manager.py — Module 3: Data Manager
# Downloads and caches OHLCV data for trading pairs
# ============================================================

import os
import pandas as pd
import yfinance as yf

from shared.config import TRADING_PAIRS, START_DATE, END_DATE, DATA_CACHE_DIR


class DataManager:
    """
    Handles downloading, caching, and loading of OHLCV
    (Open, High, Low, Close, Volume) price data.

    Features
    --------
    - In-memory LRU cache for fast repeated access
    - Disk cache (CSV) to avoid redundant API calls
    - Graceful error handling for unavailable symbols
    """

    def __init__(self, cache_dir: str = DATA_CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._mem_cache: dict[str, pd.DataFrame] = {}

    # ── Public ───────────────────────────────────────────────

    def get_ohlcv(
        self,
        symbol: str,
        start: str = START_DATE,
        end: str = END_DATE,
    ) -> pd.DataFrame:
        """
        Return OHLCV DataFrame for *symbol* between *start* and *end*.
        Checks memory cache → disk cache → downloads from Yahoo Finance.
        """
        key = f"{symbol}_{start}_{end}"

        # 1. Memory cache hit
        if key in self._mem_cache:
            return self._mem_cache[key]

        # 2. Disk cache hit
        csv_path = self._csv_path(symbol, start, end)
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            self._mem_cache[key] = df
            print(f"[DataManager] Loaded {symbol} from disk cache.")
            return df

        # 3. Download from Yahoo Finance
        df = self._download(symbol, start, end)
        df.to_csv(csv_path)
        self._mem_cache[key] = df
        return df

    def get_live_price(self, symbol: str) -> pd.DataFrame:
        """Fetch the latest intraday 1-minute data for the symbol."""
        try:
            # Use period=5d to ensure we get data even if the market is currently closed
            df = yf.download(symbol, period="5d", interval="1m", progress=False)
            if df.empty:
                return None
            
            # yfinance creates MultiIndex columns sometimes, let's flatten them
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            df.columns = [c.lower() for c in df.columns]
            return df
        except Exception as e:
            print(f"[DataManager] Failed to fetch live data for {symbol}: {e}")
            return None

    def get_all_live_pairs(self) -> dict[str, pd.DataFrame]:
        data = {}
        for pair in TRADING_PAIRS:
            data[pair] = self.get_live_price(pair)
        return data

    def get_all_pairs(
        self,
        start: str = START_DATE,
        end: str = END_DATE,
    ) -> dict[str, pd.DataFrame]:
        """
        Download OHLCV data for every pair in TRADING_PAIRS.
        Returns a dict {symbol: DataFrame}.  Skips failed symbols.
        """
        data: dict[str, pd.DataFrame] = {}
        for symbol in TRADING_PAIRS:
            try:
                data[symbol] = self.get_ohlcv(symbol, start, end)
            except Exception as exc:
                print(f"[DataManager] ⚠  Skipping {symbol}: {exc}")
        if not data:
            raise RuntimeError("No trading pair data could be downloaded.")
        return data

    def describe(self, symbol: str) -> None:
        """Print a summary of the cached data for *symbol*."""
        df = self.get_ohlcv(symbol)
        print(f"\n{'─'*50}")
        print(f"  Symbol : {symbol}")
        print(f"  Rows   : {len(df)}")
        print(f"  From   : {df.index[0].date()}")
        print(f"  To     : {df.index[-1].date()}")
        print(f"  Cols   : {list(df.columns)}")
        print(df.tail(3).to_string())
        print(f"{'─'*50}\n")

    # ── Private ──────────────────────────────────────────────

    def _download(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        print(f"[DataManager] ⬇  Downloading {symbol}  ({start} → {end}) ...")
        ticker = yf.Ticker(symbol)
        raw = ticker.history(start=start, end=end, auto_adjust=True)

        if raw.empty:
            raise ValueError(f"No data returned for symbol '{symbol}'")

        df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index.name = "date"
        print(f"[DataManager] ✓  {symbol}: {len(df)} bars downloaded.")
        return df

    def _csv_path(self, symbol: str, start: str, end: str) -> str:
        safe = symbol.replace("/", "_").replace("-", "_")
        return os.path.join(self.cache_dir, f"{safe}_{start}_{end}.csv")


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    dm = DataManager()
    dm.describe("AAPL")
    dm.describe("BTC-USD")
