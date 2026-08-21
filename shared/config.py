# ============================================================
# config.py — GeneTrader Configuration
# Technical Trading Strategy Optimization using Genetic Algorithms
# 6th Semester Soft Computing Project | School of CSE & IS
# ============================================================

# ── Trading Pairs (stocks + crypto) ─────────────────────────
TRADING_PAIRS = [
    "AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", 
    "NVDA", "META", "NFLX", "AMD", "INTC",
    "JPM", "V", "DIS", "UBER", "PYPL",
    "SQ", "SHOP", "SPOT", "CRM", "ABNB",
    "BTC-USD", "ETH-USD"
]

# ── Historical Data Window ───────────────────────────────────
START_DATE = "2020-01-01"
END_DATE   = "2024-01-01"

# ── Capital ──────────────────────────────────────────────────
INITIAL_CAPITAL = 10_000.0   # USD

# ── GA Hyper-parameters ──────────────────────────────────────
POPULATION_SIZE  = 50        # number of individuals per generation
NUM_GENERATIONS  = 30        # total evolutionary generations
CROSSOVER_PROB   = 0.70      # probability of crossover (cx)
MUTATION_PROB    = 0.20      # probability of mutation
TOURNAMENT_SIZE  = 3         # tournament selection k
ELITISM_SIZE     = 5         # top-k individuals carried forward unchanged
NUM_PROCESSES    = 4         # parallel workers for fitness evaluation

# ── Strategy Gene Bounds ─────────────────────────────────────
# Chromosome layout (9 genes, all floats — decoded in StrategyGenerator):
#   [0] indicator_type   0=MA_CROSSOVER | 1=RSI | 2=MACD_RSI
#   [1] fast_period      int in [5, 50]
#   [2] slow_period      int in [20, 200]
#   [3] rsi_period       int in [7, 21]
#   [4] rsi_oversold     float in [20, 40]
#   [5] rsi_overbought   float in [60, 80]
#   [6] stop_loss_pct    float in [0.01, 0.10]
#   [7] take_profit_pct  float in [0.02, 0.20]
#   [8] pair_index       int in [0, len(TRADING_PAIRS)-1]

GENE_BOUNDS = [
    (0.0,  2.0),    # [0] indicator_type
    (5.0,  50.0),   # [1] fast_period
    (20.0, 200.0),  # [2] slow_period
    (7.0,  21.0),   # [3] rsi_period
    (20.0, 40.0),   # [4] rsi_oversold
    (60.0, 80.0),   # [5] rsi_overbought
    (0.01, 0.10),   # [6] stop_loss_pct
    (0.02, 0.20),   # [7] take_profit_pct
    (0.0,  float(len(TRADING_PAIRS) - 1)),  # [8] pair_index
]

INDICATOR_NAMES = {0: "MA_CROSSOVER", 1: "RSI", 2: "MACD_RSI"}

# ── Fitness ──────────────────────────────────────────────────
# Primary fitness metric used by GA
# Options: "sharpe" | "total_return" | "calmar"
FITNESS_METRIC = "sharpe"

# Minimum trades required in a backtest to avoid trivial strategies
MIN_TRADES = 5

# ── File Paths ───────────────────────────────────────────────
RESULTS_DIR          = "results"
BEST_STRATEGY_FILE   = "results/best_strategy.json"
LIVE_STRATEGY_FILE   = "results/live_strategy.json"
EVOLUTION_LOG_FILE   = "results/evolution_log.csv"
DATA_CACHE_DIR       = "data_cache"
