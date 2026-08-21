# ============================================================
# strategy_generator.py — Module 1: Strategy Generator
# Decodes GA chromosomes into rule-based trading strategies
# and computes technical indicators on OHLCV data.
# ============================================================

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict, field
from typing import Tuple

from shared.config import GENE_BOUNDS, INDICATOR_NAMES, TRADING_PAIRS


# ── Strategy Dataclass ───────────────────────────────────────

@dataclass
class Strategy:
    """
    A fully decoded trading strategy.
    Produced by StrategyGenerator.decode().
    """
    indicator_type:   str   # "MA_CROSSOVER" | "RSI" | "MACD_RSI"
    fast_period:      int   # short EMA/SMA window
    slow_period:      int   # long EMA/SMA window
    rsi_period:       int   # RSI lookback
    rsi_oversold:     float # buy threshold for RSI
    rsi_overbought:   float # sell threshold for RSI
    stop_loss_pct:    float # e.g. 0.05 → 5% stop-loss
    take_profit_pct:  float # e.g. 0.10 → 10% take-profit
    pair:             str   # trading symbol, e.g. "AAPL"

    # populated after evaluation
    fitness:          float = 0.0
    total_return:     float = 0.0
    sharpe_ratio:     float = 0.0
    max_drawdown:     float = 0.0
    num_trades:       int   = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        return (
            f"Strategy({self.indicator_type}, pair={self.pair}, "
            f"fast={self.fast_period}, slow={self.slow_period}, "
            f"rsi={self.rsi_period}, SL={self.stop_loss_pct:.2%}, "
            f"TP={self.take_profit_pct:.2%}) → "
            f"Sharpe={self.sharpe_ratio:.3f}, "
            f"Return={self.total_return:.2%}, "
            f"Trades={self.num_trades}"
        )


# ── StrategyGenerator ────────────────────────────────────────

class StrategyGenerator:
    """
    Module 1: Strategy Generator

    Responsibilities
    ────────────────
    1. Decode a GA chromosome (list of floats) into a Strategy object.
    2. Compute technical indicators (SMA, EMA, RSI, MACD) on OHLCV data.
    3. Generate buy/sell signal columns on the price DataFrame.
    """

    # ── Decoding ─────────────────────────────────────────────

    @staticmethod
    def decode(chromosome: list[float]) -> Strategy:
        """
        Map a raw chromosome (9 floats) to a Strategy.

        Chromosome layout
        -----------------
        [0] indicator_type   ∈ {0, 1, 2}
        [1] fast_period      ∈ [5, 50]
        [2] slow_period      ∈ [20, 200]
        [3] rsi_period       ∈ [7, 21]
        [4] rsi_oversold     ∈ [20, 40]
        [5] rsi_overbought   ∈ [60, 80]
        [6] stop_loss_pct    ∈ [0.01, 0.10]
        [7] take_profit_pct  ∈ [0.02, 0.20]
        [8] pair_index       ∈ [0, len(TRADING_PAIRS)-1]
        """
        ind_type_raw  = int(round(np.clip(chromosome[0], 0, 2)))
        fast_period   = max(2, int(round(np.clip(chromosome[1], *GENE_BOUNDS[1]))))
        slow_period   = int(round(np.clip(chromosome[2], *GENE_BOUNDS[2])))
        rsi_period    = int(round(np.clip(chromosome[3], *GENE_BOUNDS[3])))
        rsi_oversold  = float(np.clip(chromosome[4], *GENE_BOUNDS[4]))
        rsi_overbought= float(np.clip(chromosome[5], *GENE_BOUNDS[5]))
        stop_loss_pct = float(np.clip(chromosome[6], *GENE_BOUNDS[6]))
        take_profit_pct=float(np.clip(chromosome[7], *GENE_BOUNDS[7]))
        pair_idx      = int(round(np.clip(chromosome[8], 0, len(TRADING_PAIRS) - 1)))

        # Guarantee fast < slow for MA strategies
        if fast_period >= slow_period:
            fast_period = max(2, slow_period - 5)

        return Strategy(
            indicator_type   = INDICATOR_NAMES[ind_type_raw],
            fast_period      = fast_period,
            slow_period      = slow_period,
            rsi_period       = rsi_period,
            rsi_oversold     = rsi_oversold,
            rsi_overbought   = rsi_overbought,
            stop_loss_pct    = stop_loss_pct,
            take_profit_pct  = take_profit_pct,
            pair             = TRADING_PAIRS[pair_idx],
        )

    @staticmethod
    def random_chromosome() -> list[float]:
        """Generate one random chromosome within gene bounds."""
        return [
            float(np.random.uniform(lo, hi))
            for lo, hi in GENE_BOUNDS
        ]

    # ── Indicator Computation ─────────────────────────────────

    @staticmethod
    def compute_sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    @staticmethod
    def compute_ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def compute_rsi(series: pd.Series, period: int) -> pd.Series:
        """Wilder's RSI."""
        delta  = series.diff()
        gain   = delta.clip(lower=0)
        loss   = (-delta).clip(lower=0)
        avg_g  = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_l  = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        rs     = avg_g / avg_l.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def compute_macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Tuple[pd.Series, pd.Series]:
        """Returns (macd_line, signal_line)."""
        ema_fast   = series.ewm(span=fast,   adjust=False).mean()
        ema_slow   = series.ewm(span=slow,   adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line= macd_line.ewm(span=signal, adjust=False).mean()
        return macd_line, signal_line

    # ── Signal Generation ─────────────────────────────────────

    def generate_signals(
        self,
        df: pd.DataFrame,
        strategy: Strategy,
    ) -> pd.DataFrame:
        """
        Attach 'signal' column to *df*:
            +1 → Buy
            -1 → Sell
             0 → Hold

        Parameters
        ----------
        df       : OHLCV DataFrame with columns open/high/low/close/volume
        strategy : decoded Strategy object
        """
        df = df.copy()
        close = df["close"]

        if strategy.indicator_type == "MA_CROSSOVER":
            df = self._signals_ma_crossover(df, close, strategy)

        elif strategy.indicator_type == "RSI":
            df = self._signals_rsi(df, close, strategy)

        elif strategy.indicator_type == "MACD_RSI":
            df = self._signals_macd_rsi(df, close, strategy)

        else:
            df["signal"] = 0

        df["signal"] = df["signal"].fillna(0).astype(int)
        return df

    # ── Private signal helpers ────────────────────────────────

    def _signals_ma_crossover(
        self, df: pd.DataFrame, close: pd.Series, s: Strategy
    ) -> pd.DataFrame:
        """Buy when fast EMA crosses above slow EMA; sell on cross-below."""
        fast_ema = self.compute_ema(close, s.fast_period)
        slow_ema = self.compute_ema(close, s.slow_period)

        df["ema_fast"] = fast_ema
        df["ema_slow"] = slow_ema

        # Cross-over detection
        cross_above = (fast_ema > slow_ema) & (fast_ema.shift(1) <= slow_ema.shift(1))
        cross_below = (fast_ema < slow_ema) & (fast_ema.shift(1) >= slow_ema.shift(1))

        df["signal"] = 0
        df.loc[cross_above, "signal"] = 1
        df.loc[cross_below, "signal"] = -1
        return df

    def _signals_rsi(
        self, df: pd.DataFrame, close: pd.Series, s: Strategy
    ) -> pd.DataFrame:
        """Buy on oversold bounce; sell on overbought rejection."""
        rsi = self.compute_rsi(close, s.rsi_period)
        df["rsi"] = rsi

        buy  = (rsi < s.rsi_oversold)  & (rsi.shift(1) >= s.rsi_oversold)
        sell = (rsi > s.rsi_overbought) & (rsi.shift(1) <= s.rsi_overbought)

        df["signal"] = 0
        df.loc[buy,  "signal"] = 1
        df.loc[sell, "signal"] = -1
        return df

    def _signals_macd_rsi(
        self, df: pd.DataFrame, close: pd.Series, s: Strategy
    ) -> pd.DataFrame:
        """MACD cross + RSI confirmation filter."""
        macd, sig_line = self.compute_macd(
            close, fast=s.fast_period, slow=s.slow_period
        )
        rsi = self.compute_rsi(close, s.rsi_period)

        df["macd"]        = macd
        df["macd_signal"] = sig_line
        df["rsi"]         = rsi

        macd_cross_up   = (macd > sig_line) & (macd.shift(1) <= sig_line.shift(1))
        macd_cross_down = (macd < sig_line) & (macd.shift(1) >= sig_line.shift(1))

        rsi_not_overbought = rsi < s.rsi_overbought
        rsi_not_oversold   = rsi > s.rsi_oversold

        df["signal"] = 0
        df.loc[macd_cross_up   & rsi_not_overbought, "signal"] = 1
        df.loc[macd_cross_down & rsi_not_oversold,   "signal"] = -1
        return df


# ── Quick sanity test ─────────────────────────────────────────
if __name__ == "__main__":
    import random
    sg = StrategyGenerator()
    chrom = sg.random_chromosome()
    print("Chromosome:", chrom)
    strat = sg.decode(chrom)
    print("Decoded strategy:", strat.summary())
