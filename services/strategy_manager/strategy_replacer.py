# ============================================================
# strategy_replacer.py — Module 5: Strategy Replacer
# Compares the newly evolved (offline) best strategy against
# the currently deployed (live/online) strategy and
# automatically replaces it if the new one is superior.
# ============================================================

import json
import os
from datetime import datetime

from shared.config import LIVE_STRATEGY_FILE, BEST_STRATEGY_FILE, RESULTS_DIR
from services.compute_engine.strategy_generator import Strategy, StrategyGenerator


class StrategyReplacer:
    """
    Module 5: Strategy Replacer

    Responsibilities
    ────────────────
    1. Load the currently deployed (live) strategy from disk.
    2. Compare live vs new offline strategy using fitness.
    3. Replace live strategy if offline is strictly better.
    4. Persist strategies as JSON for audit trail.

    This implements the "offline-online switching" innovation
    described in the GeneTrader project specification.
    """

    def __init__(
        self,
        best_strategy_path:  str = BEST_STRATEGY_FILE,
        live_strategy_path:  str = LIVE_STRATEGY_FILE,
    ):
        self.best_path = best_strategy_path
        self.live_path = live_strategy_path
        os.makedirs(RESULTS_DIR, exist_ok=True)

    # ── Public ────────────────────────────────────────────────

    def compare_and_replace(
        self,
        offline_strategy: Strategy,
        verbose: bool = True,
    ) -> tuple[Strategy, bool]:
        """
        Compare *offline_strategy* (newly evolved) against the
        currently deployed live strategy.

        Returns
        -------
        (active_strategy, was_replaced)
            active_strategy : the strategy that should be deployed.
            was_replaced    : True if the live strategy was swapped.
        """
        live_strategy = self._load_live()

        # First run — no live strategy exists yet
        if live_strategy is None:
            self._deploy(offline_strategy)
            if verbose:
                print(
                    "\n[StrategyReplacer] No live strategy found. "
                    "Deploying evolved strategy as live."
                )
                print(f"  → {offline_strategy.summary()}")
            return offline_strategy, True

        was_replaced = offline_strategy.fitness > live_strategy.fitness

        if verbose:
            self._print_comparison(live_strategy, offline_strategy, was_replaced)

        if was_replaced:
            self._deploy(offline_strategy)
            return offline_strategy, True
        else:
            return live_strategy, False

    def save_best(self, strategy: Strategy) -> None:
        """Persist the offline best strategy to disk."""
        self._write_json(strategy, self.best_path)
        print(f"[StrategyReplacer] Best strategy saved → {self.best_path}")

    def load_best(self) -> Strategy | None:
        """Load the last saved offline best strategy."""
        return self._read_json(self.best_path)

    def load_live(self) -> Strategy | None:
        """Load the currently deployed live strategy."""
        return self._load_live()

    # ── Private ───────────────────────────────────────────────

    def _load_live(self) -> Strategy | None:
        return self._read_json(self.live_path)

    def _deploy(self, strategy: Strategy) -> None:
        self._write_json(strategy, self.live_path)
        print(f"[StrategyReplacer] ✓ Live strategy updated → {self.live_path}")

    @staticmethod
    def _write_json(strategy: Strategy, path: str) -> None:
        data = strategy.to_dict()
        data["_deployed_at"] = datetime.now().isoformat()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _read_json(path: str) -> Strategy | None:
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        # Strip metadata keys not in Strategy
        data.pop("_deployed_at", None)
        return Strategy(**{k: v for k, v in data.items() if k in Strategy.__dataclass_fields__})

    @staticmethod
    def _print_comparison(
        live: Strategy, offline: Strategy, will_replace: bool
    ) -> None:
        decision = "✓ REPLACING live strategy" if will_replace else "✗ Keeping live strategy"
        print(f"\n{'═'*60}")
        print(f"  Strategy Replacer — Offline vs Online Comparison")
        print(f"{'─'*60}")
        print(f"  {'LIVE (deployed)':<18}: {live.indicator_type:<12} "
              f"| pair={live.pair:<9} | fitness={live.fitness:+.4f}")
        print(f"  {'OFFLINE (evolved)':<18}: {offline.indicator_type:<12} "
              f"| pair={offline.pair:<9} | fitness={offline.fitness:+.4f}")
        print(f"{'─'*60}")
        print(f"  Decision → {decision}")
        print(f"{'═'*60}\n")
