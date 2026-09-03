# 📈 GeneTrader EDMA: Real-Time Algorithmic Trading Screener

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![React](https://img.shields.io/badge/React-18.0+-61DAFB.svg)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)

**GeneTrader EDMA** is an institutional-grade, real-time quantitative trading platform. It utilizes a **Genetic Algorithm (GA)** to autonomously evolve and optimize mathematical trading strategies, and an **Event-Driven Microservices Architecture (EDMA)** to apply those strategies to live market data streams.

Instead of relying on static, human-coded trading rules, GeneTrader continuously evaluates 22 major equities and cryptocurrencies in real-time, streaming the **Top 10 highest-conviction trading signals** directly to a modern, Groww-style React dashboard via WebSockets.

---

## ✨ Key Features

- 🧬 **Genetic Algorithm Optimization:** Uses the `DEAP` framework to backtest thousands of parameter combinations across historical data, optimizing technical indicators (like RSI and MACD) for maximum **Sharpe Ratio** (risk-adjusted return).
- ⚡ **Event-Driven Microservices:** Completely decentralized architecture using Celery and Redis to separate heavy AI compute tasks from real-time data ingestion.
- 📡 **Live Market Screener:** Autonomously scans a 5-day rolling window of 1-minute intraday data for 22 assets (e.g., AAPL, NVDA, TSLA, BTC) every 15 seconds.
- 🔌 **Real-Time WebSockets:** The FastAPI backend pushes live prices and AI recommendations to the client instantly over a persistent TCP connection—zero page refreshes required.
- 💻 **Premium React Dashboard:** A beautiful, responsive UI featuring a live market overview grid, dynamic daily percentage changes, and a real-time fitness trajectory chart.

---

## 🏗️ System Architecture

GeneTrader is divided into four highly-scalable Dockerized microservices orchestrated via `docker-compose`, with **Redis** acting as the central nervous system (message broker and state store).

1. **Data Ingestion Service (Python):** Continuously polls Yahoo Finance for live market ticks and buffers a rolling window into Redis.
2. **Strategy Manager (Python):** The execution bot. It reads the GA's evolved parameters, maps them against the live data in Redis, calculates an "Expected ROI" confidence score for all 22 assets, and generates the Top 10 list.
3. **Compute Engine (Celery Workers):** A distributed cluster that handles the computationally heavy Genetic Algorithm backtesting asynchronously.
4. **API Gateway (FastAPI):** Exposes REST endpoints to trigger the AI and maintains the WebSocket connection to stream the live Top 10 signals and prices to the frontend.

---

## 🛠️ Tech Stack

### Backend & AI
- **Python 3.11**
- **DEAP:** Distributed Evolutionary Algorithms in Python
- **FastAPI:** High-performance async web framework
- **Celery:** Distributed task queue
- **Pandas / NumPy:** Financial data manipulation

### Infrastructure & Data
- **Redis:** In-memory message broker and low-latency state store
- **Docker & Docker Compose:** Containerization and orchestration
- **Yahoo Finance API (`yfinance`):** Live market data ingestion

### Frontend
- **React + Vite:** Lightning-fast UI rendering
- **Recharts:** Dynamic fitness trajectory graphing
- **Lucide React:** Modern iconography

---

## 🚀 Getting Started

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- [Node.js](https://nodejs.org/) installed (for running the frontend locally).

### 1. Spin up the Backend (Microservices)
Clone the repository and build the Docker containers. This will automatically start Redis, FastAPI, Celery, and the Data Ingestion services.

```bash
git clone https://github.com/Nithi7518/genetrader-edma.git
cd genetrader-edma
docker-compose up --build -d
```
*(Wait ~15 seconds for the ingestion service to pull the first batch of live market data into Redis).*

### 2. Start the Frontend Dashboard
Open a new terminal, navigate to the `frontend` folder, and start the Vite dev server.

```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173` in your browser.

---

## 💡 How to Use the Dashboard

1. **View Live Markets:** Upon loading the dashboard, the "Live Market Overview" grid will instantly populate with 22 stocks, showing their live prices and day-change percentages.
2. **Evolve a Strategy:** Click the **"Evolve New Strategy"** button on the left panel. This triggers the Celery workers to run the Genetic Algorithm.
3. **Watch the AI Learn:** Observe the *Fitness Trajectory* chart as the AI breeds successive generations to find the perfect trading parameters.
4. **Live Trading Signals:** The moment the evolution completes (Generation 30), the Strategy Manager saves the rules and begins scanning the live market. Your **Top 10 AI Recommendations** panel will instantly light up with real-time `BUY` signals!

---

## 👨‍💻 Credits & Acknowledgements

Developed as a 6th Semester Soft Computing Project at the School of Computer Science & Information Systems.

A special thanks to the maintainers of **DEAP**, **FastAPI**, **Redis**, and **Celery** for providing the incredible open-source tools that made this architecture possible.

---
*Disclaimer: This project is for educational and research purposes only. Do not use these signals for real financial trading.*
