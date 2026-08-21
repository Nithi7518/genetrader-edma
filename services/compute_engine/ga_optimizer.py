# ============================================================
# ga_optimizer.py — Module 2: GA Optimizer
# Uses DEAP to evolve a population of trading strategy
# chromosomes across multiple generations.
# ============================================================

import os
import csv
import json
import random
import numpy as np
from copy import deepcopy
from multiprocessing import Pool
from typing import Callable

from deap import base, creator, tools, algorithms

from shared.config import (
    GENE_BOUNDS, POPULATION_SIZE, NUM_GENERATIONS,
    CROSSOVER_PROB, MUTATION_PROB, TOURNAMENT_SIZE,
    ELITISM_SIZE, NUM_PROCESSES, EVOLUTION_LOG_FILE, RESULTS_DIR,
)
from services.compute_engine.strategy_generator import StrategyGenerator

# ── DEAP type registration (module-level, done once) ─────────
if not hasattr(creator, "FitnessMax"):
    creator.create("FitnessMax", base.Fitness, weights=(1.0,))
if not hasattr(creator, "Individual"):
    creator.create("Individual", list, fitness=creator.FitnessMax)


def _clip_individual(individual: list) -> list:
    """Keep every gene within its defined bounds after mutation."""
    for i, (lo, hi) in enumerate(GENE_BOUNDS):
        individual[i] = float(np.clip(individual[i], lo, hi))
    return individual


class GAOptimizer:
    """
    Module 2: GA Optimizer

    Implements a steady-state genetic algorithm using DEAP with:
    - Tournament selection
    - Blend crossover (cxBlend)
    - Gaussian mutation with bound-clipping
    - Elitism (top-k survive unchanged)
    - Optional multiprocessing fitness evaluation
    - Evolution log written to CSV
    """

    def __init__(
        self,
        fitness_fn: Callable[[list], tuple[float]],
        n_processes: int = NUM_PROCESSES,
    ):
        """
        Parameters
        ----------
        fitness_fn  : function(chromosome) → (float,)
                      Called by DEAP for every individual each generation.
        n_processes : number of parallel worker processes (set 1 to disable).
        """
        self.fitness_fn  = fitness_fn
        self.n_processes = n_processes
        self._sg         = StrategyGenerator()
        self._toolbox    = self._build_toolbox()

        os.makedirs(RESULTS_DIR, exist_ok=True)

    # ── Public ────────────────────────────────────────────────

    def run(self) -> tuple[list, list]:
        """
        Run the full GA and return (best_chromosome, evolution_log).

        evolution_log : list of dicts with generation stats.
        """
        pop         = self._init_population()
        log_rows    = []
        best_ind    = None
        best_fit    = float("-inf")

        print(f"\n{'━'*58}")
        print(f"  GeneTrader — Genetic Algorithm Optimizer")
        print(f"  Population: {POPULATION_SIZE}  |  Generations: {NUM_GENERATIONS}")
        print(f"  CX={CROSSOVER_PROB}  MUT={MUTATION_PROB}  Elitism={ELITISM_SIZE}")
        print(f"{'━'*58}\n")

        # Evaluate initial population
        self._eval_population(pop)

        for gen in range(1, NUM_GENERATIONS + 1):
            # ── Elitism: carry over top-k unchanged ──────────
            elites = tools.selBest(pop, ELITISM_SIZE)
            elites = [deepcopy(ind) for ind in elites]

            # ── Selection ────────────────────────────────────
            offspring = self._toolbox.select(pop, len(pop) - ELITISM_SIZE)
            offspring = [deepcopy(ind) for ind in offspring]

            # ── Crossover ────────────────────────────────────
            for c1, c2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < CROSSOVER_PROB:
                    self._toolbox.mate(c1, c2)
                    del c1.fitness.values
                    del c2.fitness.values

            # ── Mutation ─────────────────────────────────────
            for ind in offspring:
                if random.random() < MUTATION_PROB:
                    self._toolbox.mutate(ind)
                    _clip_individual(ind)
                    del ind.fitness.values

            # ── Re-evaluate invalids ──────────────────────────
            invalids = [ind for ind in offspring if not ind.fitness.valid]
            self._eval_population(invalids)

            # ── New population = elites + offspring ───────────
            pop = elites + offspring

            # ── Statistics ───────────────────────────────────
            fits       = [ind.fitness.values[0] for ind in pop]
            gen_best   = max(fits)
            gen_avg    = np.mean(fits)
            gen_std    = np.std(fits)
            gen_best_ind = tools.selBest(pop, 1)[0]

            if gen_best > best_fit:
                best_fit = gen_best
                best_ind = deepcopy(gen_best_ind)

            row = {
                "generation": gen,
                "best_fitness": round(gen_best, 5),
                "avg_fitness" : round(gen_avg, 5),
                "std_fitness" : round(gen_std, 5),
            }
            log_rows.append(row)

            strat_name = self._sg.decode(list(gen_best_ind)).indicator_type
            print(
                f"  Gen {gen:>3}/{NUM_GENERATIONS}  "
                f"│ Best={gen_best:+.4f}  "
                f"│ Avg={gen_avg:+.4f}  "
                f"│ Std={gen_std:.4f}  "
                f"│ Strategy={strat_name}"
            )

        self._write_log(log_rows)
        print(f"\n[GAOptimizer] ✓ Evolution complete. Best fitness = {best_fit:.4f}")
        return list(best_ind), log_rows

    # ── Private ───────────────────────────────────────────────

    def _init_population(self) -> list:
        """Create POPULATION_SIZE random individuals."""
        pop = []
        for _ in range(POPULATION_SIZE):
            chrom = self._sg.random_chromosome()
            ind   = creator.Individual(chrom)
            pop.append(ind)
        return pop

    def _eval_population(self, pop: list) -> None:
        """Evaluate fitness for all individuals in *pop* (modifies in-place)."""
        if self.n_processes > 1:
            with Pool(processes=self.n_processes) as pool:
                fitnesses = pool.map(self.fitness_fn, [list(ind) for ind in pop])
        else:
            fitnesses = [self.fitness_fn(list(ind)) for ind in pop]

        for ind, fit in zip(pop, fitnesses):
            ind.fitness.values = fit

    def _build_toolbox(self) -> base.Toolbox:
        toolbox = base.Toolbox()

        # Selection
        toolbox.register(
            "select",
            tools.selTournament,
            tournsize=TOURNAMENT_SIZE,
        )

        # Crossover — blend crossover (α=0.5)
        toolbox.register("mate", tools.cxBlend, alpha=0.5)

        # Mutation — Gaussian noise on each gene
        toolbox.register(
            "mutate",
            tools.mutGaussian,
            mu=0,
            sigma=0.1,
            indpb=0.3,  # probability per gene
        )

        return toolbox

    def _write_log(self, rows: list[dict]) -> None:
        with open(EVOLUTION_LOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"[GAOptimizer] Evolution log saved → {EVOLUTION_LOG_FILE}")
