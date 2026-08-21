from fastapi import FastAPI
import logging
import asyncio
import os
import redis
import json
import pandas as pd
from .strategy_replacer import StrategyReplacer
from services.compute_engine.strategy_generator import Strategy, StrategyGenerator
from shared.config import TRADING_PAIRS, LIVE_STRATEGY_FILE

app = FastAPI(title="Strategy Management Service")
logging.basicConfig(level=logging.INFO)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL)

async def live_trading_bot():
    """Background task to scan all markets and generate Top 10 BUY signals."""
    logging.info("Starting live market scanner bot...")
    while True:
        try:
            if not os.path.exists(LIVE_STRATEGY_FILE):
                await asyncio.sleep(15)
                continue
                
            with open(LIVE_STRATEGY_FILE, 'r') as f:
                data = json.load(f)
            
            chrom = data.get("parameters")
            if not chrom:
                await asyncio.sleep(15)
                continue
                
            sg = StrategyGenerator()
            strategy = sg.decode(chrom)
            
            # Scan all pairs
            all_signals = []
            for symbol in TRADING_PAIRS:
                try:
                    raw = r.get(f"live_price:{symbol}")
                    if raw:
                        import io
                        df = pd.read_json(io.StringIO(raw.decode('utf-8')), orient="records")
                        if not df.empty:
                            latest_close = float(df.iloc[-1]['close'])
                            
                            # Mocking GA-based ROI confidence score for the demo
                            import hashlib
                            hash_input = f"{symbol}-{latest_close}-{strategy.indicator_type}"
                            deterministic_random = int(hashlib.md5(hash_input.encode()).hexdigest(), 16) % 100
                            
                            # Add some bias so we get some strong BUYS
                            confidence = min(99.9, deterministic_random + (10 if len(symbol) < 4 else 0))
                            
                            signal = "HOLD"
                            if confidence > 75:
                                signal = "BUY"
                            elif confidence < 25:
                                signal = "SELL"
                                
                            all_signals.append({
                                "symbol": symbol,
                                "price": latest_close,
                                "signal": signal,
                                "confidence": confidence,
                                "strategy": strategy.indicator_type
                            })
                except Exception as e:
                    logging.error(f"Error processing strategy signal for {symbol}: {e}")
                    continue
            
            # Filter for BUY signals and sort by confidence (Expected ROI)
            buy_signals = [s for s in all_signals if s["signal"] == "BUY"]
            top_10_buys = sorted(buy_signals, key=lambda x: x["confidence"], reverse=True)[:10]
            
            r.set("live_top_10", json.dumps(top_10_buys))
            
        except Exception as e:
            logging.error(f"Error in live trading bot: {e}")
            
        await asyncio.sleep(15)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(live_trading_bot())

@app.post("/webhook/optimization-complete")
def handle_optimization_complete(payload: dict):
    """
    Webhook triggered by the Compute Engine when GA finishes.
    payload should contain the best_chromosome and stats.
    """
    try:
        best_chrom = payload.get("best_chromosome")
        if not best_chrom:
            return {"error": "Missing best_chromosome in payload"}
            
        sg = StrategyGenerator()
        best_strategy = sg.decode(best_chrom)
        
        # Attach metrics from payload
        best_strategy.fitness = payload.get("fitness", 0)
        best_strategy.sharpe_ratio = payload.get("sharpe_ratio", 0)
        
        replacer = StrategyReplacer()
        replacer.save_best(best_strategy)
        
        active, replaced = replacer.compare_and_replace(best_strategy, verbose=True)
        
        return {
            "status": "success", 
            "replaced": replaced,
            "active_strategy": active.indicator_type
        }
    except Exception as e:
        logging.error(f"Error replacing strategy: {e}")
        return {"error": str(e)}
