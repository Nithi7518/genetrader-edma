# GeneTrader 🧬📈
## Technical Trading Strategy Optimization using Genetic Algorithms

> **Soft Computing Project — 6th Semester, 2026**  
> School of Computer Science Engineering and Information Systems  
> **Team:** Yajunesh M R (23BIT0399) · Nithi Viyaga Narayanan (23BIT0036) · Sanjay Chidambaram (23BIT0425)

---

## 📌 Overview

GeneTrader evolves rule-based trading strategies using a **Genetic Algorithm (GA)**.  
Strategies are encoded as chromosomes and evolved over generations to maximise the **Sharpe Ratio** on historical OHLCV data.

### Key Innovation
Unlike prior GA trading systems, GeneTrader uniquely integrates:
- **Offline optimization** (GA on historical data)
- **Automatic live strategy replacement** (if evolved strategy beats deployed one)
- **Multi-pair selection** (GA picks the best symbol + parameters jointly)
- **Parallel fitness evaluation** (multiprocessing for speed)

---

## 🗂️ Project Structure

```
geneTrader/
├── config.py              ← All hyperparameters & paths
├── data_manager.py        ← Module 3: Download & cache OHLCV data
├── strategy_generator.py  ← Module 1: Chromosome → Strategy + Indicators
├── evaluator.py           ← Module 4: Backtest engine + fitness metrics
├── ga_optimizer.py        ← Module 2: DEAP-powered GA evolution loop
├── strategy_replacer.py   ← Module 5: Offline ↔ Live strategy switching
├── main.py                ← Entry point (CLI)
├── requirements.txt       ← Python dependencies
├── data_cache/            ← Auto-created: cached CSV data
└── results/               ← Auto-created: plots, logs, JSON strategies
    ├── best_strategy.json
    ├── live_strategy.json
    ├── evolution_log.csv
    ├── evolution_fitness.png
    ├── signals_<PAIR>.png
    ├── equity_curve_<PAIR>.png
    └── pair_returns.png
```

---

## ⚙️ Setup

### 1. Clone / Download the project
```bash
cd geneTrader
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

### Full GA Pipeline (recommended)
```bash
python main.py --mode full
```

### Quick Demo (single strategy, no GA)
```bash
python main.py --mode demo --symbol AAPL
```

### Enable Parallel Fitness Evaluation
```bash
python main.py --mode full --processes 4
```

### Test individual modules
```bash
python data_manager.py       # Download & describe AAPL + BTC-USD
python strategy_generator.py # Generate a random strategy
python evaluator.py          # Backtest a random strategy on AAPL
```

---

## 🧬 How the GA Works

```
┌──────────────────────────────────────────────────────────────┐
│                    GENETIC ALGORITHM LOOP                    │
│                                                              │
│  1. INITIALIZATION                                           │
│     Generate 50 random chromosomes (strategy parameters)     │
│                                                              │
│  2. FITNESS EVALUATION (parallel)                            │
│     Backtest each strategy → compute Sharpe Ratio            │
│                                                              │
│  3. SELECTION                                                │
│     Tournament selection (k=3) → pick parents               │
│                                                              │
│  4. CROSSOVER  (p=0.70)                                      │
│     Blend crossover (α=0.5) between two parent chromosomes   │
│                                                              │
│  5. MUTATION   (p=0.20)                                      │
│     Gaussian noise added to each gene                        │
│                                                              │
│  6. ELITISM                                                  │
│     Top-5 individuals survive unchanged each generation      │
│                                                              │
│  7. REPEAT for 30 generations                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 🧬 Chromosome Encoding

Each strategy is encoded as a **9-gene float chromosome**:

| Gene | Parameter        | Range        | Description              |
|------|-----------------|--------------|--------------------------|
| 0    | indicator_type  | {0, 1, 2}    | MA_CROSSOVER / RSI / MACD_RSI |
| 1    | fast_period     | [5, 50]      | Short EMA/SMA window     |
| 2    | slow_period     | [20, 200]    | Long EMA/SMA window      |
| 3    | rsi_period      | [7, 21]      | RSI lookback             |
| 4    | rsi_oversold    | [20, 40]     | RSI buy threshold        |
| 5    | rsi_overbought  | [60, 80]     | RSI sell threshold       |
| 6    | stop_loss_pct   | [1%, 10%]    | Max loss per trade       |
| 7    | take_profit_pct | [2%, 20%]    | Target gain per trade    |
| 8    | pair_index      | [0, N-1]     | Which trading symbol     |

---

## 📊 Strategies Implemented

| Strategy     | Buy Signal                        | Sell Signal                       |
|-------------|-----------------------------------|-----------------------------------|
| MA_CROSSOVER | Fast EMA crosses above Slow EMA   | Fast EMA crosses below Slow EMA   |
| RSI          | RSI drops below oversold level    | RSI rises above overbought level  |
| MACD_RSI     | MACD crosses Signal + RSI filter  | MACD crosses Signal + RSI filter  |

---

## 📈 Performance Metrics

| Metric        | Formula                                      |
|--------------|----------------------------------------------|
| Total Return  | (Final Capital − Initial Capital) / Initial  |
| Sharpe Ratio  | (Mean Excess Return / Std Dev) × √252        |
| Max Drawdown  | Max peak-to-trough decline in equity curve   |

---

## 📦 Dependencies

| Package    | Purpose                          |
|-----------|----------------------------------|
| `deap`    | Genetic Algorithm framework      |
| `yfinance`| Historical OHLCV data download   |
| `pandas`  | Data manipulation                |
| `numpy`   | Numerical computation            |
| `matplotlib` | Visualisation                 |

---

## 🎓 References

1. Genetic Algorithms and Investment Strategies — Wiley
2. Evolving Trading Rules Using Genetic Programming — Springer
3. Technical Analysis and Genetic Algorithms — IEEE Xplore
4. GA-Based Optimization of Trading Strategies — ResearchGate
5. Using genetic algorithms to find technical trading rules — ScienceDirect
