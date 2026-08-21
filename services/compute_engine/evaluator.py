# ============================================================
# evaluator.py — Module 4: Evaluator
# Backtests a decoded Strategy on historical OHLCV data and
# computes performance metrics used as GA fitness.
# ============================================================

import numpy as np
import pandas as pd
from typing import Optional

from shared.config import INITIAL_CAPITAL, MIN_TRADES, FITNESS_METRIC
from services.compute_engine.strategy_generator import Strategy, StrategyGenerator


class Evaluator:
    """
    Module 4: Evaluator

    Responsibilities
    ────────────────
    1. Run a vectorised backtest for a Strategy on OHLCV data.
    2. Compute: total_return, sharpe_ratio, max_drawdown, num_trades.
    3. Return a scalar fitness value for the GA.

    Backtest rules
    ──────────────
    - Long-only (no short selling).
    - One position at a time.
    - Stop-loss and take-profit applied on each bar after entry.
    - 0.1% commission per trade (round-trip = 0.2%).
    """

    COMMISSION = 0.001          # 0.1% per side
    RISK_FREE_RATE = 0.04 / 252  # daily risk-free rate (~4% p.a.)

    def __init__(self, data_cache: Optional[dict[str, pd.DataFrame]] = None):
        """
        Parameters
        ----------
        data_cache : pre-loaded {symbol: df} dict (avoids repeated I/O).
                     If None, caller must pass df directly to evaluate_df().
        """
        self._cache = data_cache or {}
        self._sg    = StrategyGenerator()

    # ── Public API ────────────────────────────────────────────

    def evaluate(self, chromosome: list[float]) -> tuple[float]:
        """
        Decode *chromosome* → Strategy → backtest → return (fitness,).
        This is the function DEAP calls during evolution.
        """
        strategy = self._sg.decode(chromosome)
        df = self._cache.get(strategy.pair)
        if df is None or df.empty:
            return (-999.0,)          # penalise missing data

        return (self.evaluate_df(df, strategy),)

    def evaluate_df(
        self, df: pd.DataFrame, strategy: Strategy
    ) -> float:
        """
        Run a full backtest and attach metrics to *strategy* in-place.
        Returns the scalar fitness value.
        """
        try:
            df_sig = self._sg.generate_signals(df, strategy)
            metrics = self._backtest(df_sig, strategy)
        except Exception:
            metrics = self._empty_metrics()

        strategy.total_return  = metrics["total_return"]
        strategy.sharpe_ratio  = metrics["sharpe_ratio"]
        strategy.max_drawdown  = metrics["max_drawdown"]
        strategy.num_trades    = metrics["num_trades"]

        fitness = self._compute_fitness(metrics)
        strategy.fitness = fitness
        return fitness

    def metrics_report(self, strategy: Strategy) -> str:
        return (
            f"\n{'═'*55}\n"
            f"  Strategy  : {strategy.indicator_type}  │  Pair: {strategy.pair}\n"
            f"  Parameters: fast={strategy.fast_period}, slow={strategy.slow_period}, "
            f"rsi={strategy.rsi_period}\n"
            f"  SL={strategy.stop_loss_pct:.2%}  TP={strategy.take_profit_pct:.2%}\n"
            f"{'─'*55}\n"
            f"  Total Return  : {strategy.total_return:+.2%}\n"
            f"  Sharpe Ratio  : {strategy.sharpe_ratio:.4f}\n"
            f"  Max Drawdown  : {strategy.max_drawdown:.2%}\n"
            f"  Num Trades    : {strategy.num_trades}\n"
            f"  Fitness       : {strategy.fitness:.4f}\n"
            f"{'═'*55}"
        )

    # ── Backtest engine ───────────────────────────────────────

    def _backtest(
        self, df: pd.DataFrame, strategy: Strategy
    ) -> dict:
        capital     = INITIAL_CAPITAL
        equity_curve= [capital]
        in_position = False
        entry_price = 0.0
        entry_idx   = 0
        num_trades  = 0
        daily_rets  = []

        close  = df["close"].values
        signal = df["signal"].values
        n      = len(close)

        for i in range(1, n):
            prev_cap = capital

            if not in_position:
                # Entry on buy signal
                if signal[i - 1] == 1:
                    in_position = True
                    entry_price = close[i] * (1 + self.COMMISSION)
                    entry_idx   = i
            else:
                # Simulate stop-loss and take-profit on current bar
                pnl_pct = (close[i] - entry_price) / entry_price

                exit_triggered = False
                exit_price     = close[i]

                if pnl_pct <= -strategy.stop_loss_pct:      # stop-loss hit
                    exit_price      = entry_price * (1 - strategy.stop_loss_pct)
                    exit_triggered  = True
                elif pnl_pct >= strategy.take_profit_pct:   # take-profit hit
                    exit_price      = entry_price * (1 + strategy.take_profit_pct)
                    exit_triggered  = True
                elif signal[i - 1] == -1:                   # signal exit
                    exit_triggered  = True

                if exit_triggered:
                    net_price = exit_price * (1 - self.COMMISSION)
                    capital  *= net_price / entry_price
                    in_position = False
                    num_trades += 1

            equity_curve.append(capital)
            daily_rets.append((capital - prev_cap) / prev_cap if prev_cap > 0 else 0.0)

        # Penalise strategies that trade too rarely
        if num_trades < MIN_TRADES:
            return {**self._empty_metrics(), "num_trades": num_trades}

        total_return = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL
        sharpe_ratio = self._sharpe(np.array(daily_rets))
        max_drawdown = self._max_drawdown(np.array(equity_curve))

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "num_trades"  : num_trades,
        }

    # ── Metric helpers ────────────────────────────────────────

    def _sharpe(self, daily_rets: np.ndarray) -> float:
        if len(daily_rets) < 2:
            return -999.0
        excess = daily_rets - self.RISK_FREE_RATE
        std    = np.std(excess, ddof=1)
        if std == 0:
            return 0.0
        return float(np.mean(excess) / std * np.sqrt(252))

    @staticmethod
    def _max_drawdown(equity: np.ndarray) -> float:
        peak     = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / np.where(peak == 0, 1, peak)
        return float(np.max(drawdown))

    def _compute_fitness(self, metrics: dict) -> float:
        """Map metrics to a single scalar for GA optimisation."""
        sr  = metrics["sharpe_ratio"]
        ret = metrics["total_return"]
        mdd = metrics["max_drawdown"]

        if FITNESS_METRIC == "sharpe":
            return max(sr, -10.0)
        elif FITNESS_METRIC == "total_return":
            return max(ret, -1.0)
        elif FITNESS_METRIC == "calmar":
            if mdd == 0:
                return 0.0
            return max(ret / mdd, -10.0)
        return max(sr, -10.0)

    @staticmethod
    def _empty_metrics() -> dict:
        return {
            "total_return": -1.0,
            "sharpe_ratio": -999.0,
            "max_drawdown": 1.0,
            "num_trades"  : 0,
        }


# ── Quick test ────────────────────────────────────────────────
if __name__ == "__main__":
    from data_manager import DataManager
    from strategy_generator import StrategyGenerator

    dm   = DataManager()
    data = {"AAPL": dm.get_ohlcv("AAPL")}
    ev   = Evaluator(data_cache=data)
    sg   = StrategyGenerator()

    chrom    = sg.random_chromosome()
    strat    = sg.decode(chrom)
    strat.pair = "AAPL"
    ev.evaluate_df(data["AAPL"], strat)
    print(ev.metrics_report(strat))
