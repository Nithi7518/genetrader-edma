# ============================================================
# main.py — GeneTrader Entry Point
# Technical Trading Strategy Optimization using Genetic Algorithms
#
# Authors : Yajunesh M R (23BIT0399), Nithi Viyaga Narayanan (23BIT0036),
#           Sanjay Chidambaram (23BIT0425)
# Course  : Soft Computing — 6th Semester, 2026
# School  : School of CSE & IS
# ============================================================

import os
import json
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")           # headless rendering (no display needed)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from config import (
    TRADING_PAIRS, START_DATE, END_DATE, INITIAL_CAPITAL,
    RESULTS_DIR, BEST_STRATEGY_FILE,
)
from data_manager      import DataManager
from strategy_generator import StrategyGenerator
from evaluator          import Evaluator
from ga_optimizer       import GAOptimizer
from strategy_replacer  import StrategyReplacer


# ═══════════════════════════════════════════════════════════════
#  PIPELINE
# ═══════════════════════════════════════════════════════════════

def run_pipeline(n_processes: int = 1) -> None:
    """End-to-end GeneTrader pipeline."""

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # ── Step 1: Load Data ─────────────────────────────────────
    print("\n[1/5] Loading OHLCV data for all trading pairs …")
    dm   = DataManager()
    data = dm.get_all_pairs(start=START_DATE, end=END_DATE)
    print(f"      Loaded {len(data)} pairs: {list(data.keys())}")

    # ── Step 2: Build Evaluator ───────────────────────────────
    print("\n[2/5] Initialising Evaluator …")
    evaluator = Evaluator(data_cache=data)

    # ── Step 3: Run GA ────────────────────────────────────────
    print("\n[3/5] Running Genetic Algorithm Optimizer …")
    optimizer = GAOptimizer(
        fitness_fn  = evaluator.evaluate,
        n_processes = n_processes,
    )
    best_chrom, evo_log = optimizer.run()

    # ── Step 4: Decode + Evaluate best chromosome ─────────────
    print("\n[4/5] Evaluating best evolved strategy …")
    sg           = StrategyGenerator()
    best_strategy = sg.decode(best_chrom)
    best_df       = data.get(best_strategy.pair)

    if best_df is not None:
        evaluator.evaluate_df(best_df, best_strategy)

    print(evaluator.metrics_report(best_strategy))

    # ── Step 5: Strategy Replacement ──────────────────────────
    print("\n[5/5] Running Strategy Replacer (offline ↔ live) …")
    replacer = StrategyReplacer()
    replacer.save_best(best_strategy)
    active_strategy, was_replaced = replacer.compare_and_replace(
        best_strategy, verbose=True
    )

    # ── Visualisations ────────────────────────────────────────
    print("\n[Vis] Generating result plots …")
    _plot_all(best_strategy, best_df, evo_log, data)

    print(f"\n{'✓'*3} GeneTrader pipeline complete {'✓'*3}")
    print(f"  Results saved in  : {RESULTS_DIR}/")
    print(f"  Best strategy     : {best_strategy.summary()}")
    print(f"  Plots             : {RESULTS_DIR}/*.png\n")


# ═══════════════════════════════════════════════════════════════
#  SINGLE STRATEGY DEMO
# ═══════════════════════════════════════════════════════════════

def run_demo(symbol: str = "AAPL") -> None:
    """
    Quick demo: evaluate one hard-coded strategy and plot signals.
    Useful for testing without running the full GA.
    """
    dm   = DataManager()
    df   = dm.get_ohlcv(symbol)
    sg   = StrategyGenerator()
    ev   = Evaluator(data_cache={symbol: df})

    # A hand-crafted MA-crossover strategy for demo purposes
    chrom = [0.0, 10.0, 50.0, 14.0, 30.0, 70.0, 0.05, 0.10, 0.0]
    strat = sg.decode(chrom)
    strat.pair = symbol
    ev.evaluate_df(df, strat)
    print(ev.metrics_report(strat))
    _plot_strategy_signals(strat, df, suffix="demo")


# ═══════════════════════════════════════════════════════════════
#  PLOTS
# ═══════════════════════════════════════════════════════════════

def _plot_all(strategy, df, evo_log, all_data):
    _plot_evolution(evo_log)
    if df is not None:
        _plot_strategy_signals(strategy, df)
        _plot_equity_curve(strategy, df)
    _plot_pair_returns(all_data)


def _plot_evolution(evo_log: list[dict]) -> None:
    """Plot best and average fitness across generations."""
    gens  = [r["generation"]    for r in evo_log]
    best  = [r["best_fitness"]  for r in evo_log]
    avg   = [r["avg_fitness"]   for r in evo_log]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(gens, best, "b-o", markersize=3, label="Best Fitness")
    ax.plot(gens, avg,  "r--", linewidth=1.5, label="Avg Fitness")
    ax.fill_between(gens, avg, best, alpha=0.15, color="blue")
    ax.set_xlabel("Generation")
    ax.set_ylabel("Fitness (Sharpe Ratio)")
    ax.set_title("GeneTrader — Evolution of Fitness across Generations")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, "evolution_fitness.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  [Plot] {path}")


def _plot_strategy_signals(strategy, df: pd.DataFrame, suffix: str = "") -> None:
    """Plot price with buy/sell signals overlaid."""
    sg     = StrategyGenerator()
    df_sig = sg.generate_signals(df, strategy)
    close  = df_sig["close"]

    buys  = df_sig[df_sig["signal"] ==  1]
    sells = df_sig[df_sig["signal"] == -1]

    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1]})

    ax1 = axes[0]
    ax1.plot(close.index, close, "k-", linewidth=0.8, label="Close Price")
    ax1.scatter(buys.index,  buys["close"],  marker="^", color="green",
                s=60, zorder=5, label="Buy Signal")
    ax1.scatter(sells.index, sells["close"], marker="v", color="red",
                s=60, zorder=5, label="Sell Signal")

    # Overlay indicator
    if strategy.indicator_type == "MA_CROSSOVER" and "ema_fast" in df_sig:
        ax1.plot(df_sig.index, df_sig["ema_fast"], "b-",  linewidth=1,
                 alpha=0.7, label=f"EMA({strategy.fast_period})")
        ax1.plot(df_sig.index, df_sig["ema_slow"], "r--", linewidth=1,
                 alpha=0.7, label=f"EMA({strategy.slow_period})")

    ax1.set_title(
        f"GeneTrader — {strategy.pair} | {strategy.indicator_type} Strategy\n"
        f"Sharpe={strategy.sharpe_ratio:.3f}  Return={strategy.total_return:+.2%}  "
        f"MaxDD={strategy.max_drawdown:.2%}  Trades={strategy.num_trades}"
    )
    ax1.set_ylabel("Price (USD)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.25)

    # RSI sub-plot
    ax2 = axes[1]
    if "rsi" in df_sig:
        ax2.plot(df_sig.index, df_sig["rsi"], color="purple", linewidth=0.8)
        ax2.axhline(strategy.rsi_oversold,  color="green", linestyle="--",
                    linewidth=0.8, alpha=0.7)
        ax2.axhline(strategy.rsi_overbought, color="red",   linestyle="--",
                    linewidth=0.8, alpha=0.7)
        ax2.set_ylabel("RSI")
        ax2.set_ylim(0, 100)
    else:
        ax2.set_visible(False)

    plt.tight_layout()
    tag  = f"_{suffix}" if suffix else ""
    path = os.path.join(RESULTS_DIR, f"signals_{strategy.pair}{tag}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  [Plot] {path}")


def _plot_equity_curve(strategy, df: pd.DataFrame) -> None:
    """Simulate and plot the portfolio equity curve."""
    sg     = StrategyGenerator()
    ev     = Evaluator()
    df_sig = sg.generate_signals(df, strategy)

    capital      = INITIAL_CAPITAL
    equity_curve = [capital]
    in_pos       = False
    entry_price  = 0.0
    close        = df_sig["close"].values
    signal       = df_sig["signal"].values

    for i in range(1, len(close)):
        if not in_pos:
            if signal[i - 1] == 1:
                in_pos      = True
                entry_price = close[i] * 1.001
        else:
            pnl = (close[i] - entry_price) / entry_price
            if pnl <= -strategy.stop_loss_pct or pnl >= strategy.take_profit_pct or signal[i - 1] == -1:
                exit_price = close[i] * 0.999
                capital   *= exit_price / entry_price
                in_pos     = False
        equity_curve.append(capital)

    bh_curve = INITIAL_CAPITAL * (close / close[0])   # buy & hold benchmark

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df_sig.index, equity_curve, "b-", linewidth=1.5, label="GeneTrader Strategy")
    ax.plot(df_sig.index, bh_curve,     "k--", linewidth=1,  label="Buy & Hold Benchmark", alpha=0.6)
    ax.axhline(INITIAL_CAPITAL, color="gray", linestyle=":", linewidth=0.8, alpha=0.5)
    ax.set_title(
        f"GeneTrader — Portfolio Equity Curve ({strategy.pair})\n"
        f"Final Capital: ${equity_curve[-1]:,.2f}  |  "
        f"Return: {(equity_curve[-1]/INITIAL_CAPITAL-1):+.2%}"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value (USD)")
    ax.legend()
    ax.grid(True, alpha=0.25)
    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, f"equity_curve_{strategy.pair}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  [Plot] {path}")


def _plot_pair_returns(all_data: dict) -> None:
    """Bar chart of annualised returns across all pairs."""
    labels, returns = [], []
    for sym, df in all_data.items():
        if df is not None and len(df) > 10:
            total_r = (df["close"].iloc[-1] / df["close"].iloc[0]) - 1
            years   = max(len(df) / 252, 0.1)
            ann_r   = (1 + total_r) ** (1 / years) - 1
            labels.append(sym)
            returns.append(ann_r * 100)

    colors = ["#2ecc71" if r >= 0 else "#e74c3c" for r in returns]
    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(labels, returns, color=colors, edgecolor="black", linewidth=0.5)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=9)
    ax.set_title("GeneTrader — Annualised Historical Returns by Pair")
    ax.set_ylabel("Annualised Return (%)")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    path = os.path.join(RESULTS_DIR, "pair_returns.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  [Plot] {path}")


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GeneTrader — Soft Computing Project"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "demo"],
        default="full",
        help="'full' runs complete GA pipeline; 'demo' tests a single strategy.",
    )
    parser.add_argument(
        "--symbol",
        default="AAPL",
        help="Symbol for demo mode (default: AAPL).",
    )
    parser.add_argument(
        "--processes",
        type=int,
        default=1,
        help="Parallel worker processes for fitness evaluation (default: 1).",
    )
    args = parser.parse_args()

    if args.mode == "demo":
        run_demo(symbol=args.symbol)
    else:
        run_pipeline(n_processes=args.processes)
