from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from celery.result import AsyncResult
from services.compute_engine.celery_app import celery_app
from services.compute_engine.tasks import run_optimization_task
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import redis
from shared.config import TRADING_PAIRS

app = FastAPI(title="GeneTrader EDMA API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@app.websocket("/api/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    r = redis.Redis.from_url(REDIS_URL)
    
    try:
        while True:
            # Send latest prices and day change %
            prices = {}
            for pair in TRADING_PAIRS:
                try:
                    raw = r.get(f"live_price:{pair}")
                    if raw:
                        import pandas as pd
                        import io
                        df = pd.read_json(io.StringIO(raw.decode('utf-8')), orient="records")
                        if not df.empty:
                            latest = float(df.iloc[-1]['close'])
                            # Calculate change against the start of the rolling window
                            start = float(df.iloc[0]['close'])
                            pct_change = ((latest - start) / start) * 100 if start != 0 else 0
                            
                            prices[pair] = {
                                "price": latest,
                                "change": pct_change
                            }
                except Exception as e:
                    print(f"Error processing pair {pair}: {e}")
            
            # Send top 10 signals
            top_10_raw = r.get("live_top_10")
            top_10 = json.loads(top_10_raw) if top_10_raw else []
            
            payload = {
                "prices": prices,
                "top_10": top_10
            }
            
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket Error: {e}")
        
@app.post("/api/start")
def start_optimization():
    """Enqueue a GA optimization job to the Celery workers."""
    task = run_optimization_task.delay()
    return {"task_id": task.id, "message": "Optimization job started in the background."}

@app.get("/api/status/{task_id}")
def get_status(task_id: str):
    """Poll the status of the Celery task."""
    task_result = AsyncResult(task_id, app=celery_app)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result if task_result.ready() else None
    }
    # If the task sent custom state via update_state
    if task_result.state == 'PROGRESS':
        result["progress"] = task_result.info
    
    return result

@app.get("/api/market-data/{symbol}")
def get_market_data(symbol: str):
    """Fetch the latest OHLCV data from Redis."""
    r = redis.Redis.from_url(REDIS_URL)
    raw = r.get(f"ohlcv:{symbol}")
    if raw:
        return json.loads(raw)
    return {"error": "Data not found. Data Ingestion Service might still be fetching."}
