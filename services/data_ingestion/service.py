import os
import json
import time
import logging
import redis
from .data_manager import DataManager
from shared.config import TRADING_PAIRS

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3600")) # 1 hour

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def push_to_redis(r, symbol, df):
    """Serialize the pandas DataFrame to JSON and store in Redis."""
    # Convert to orient="records" for easy parsing
    data_json = df.reset_index().to_json(orient="records", date_format="iso")
    r.set(f"ohlcv:{symbol}", data_json)
    logging.info(f"Cached {len(df)} rows for {symbol} into Redis.")

import threading

def poll_historical_data(r, dm):
    while True:
        logging.info("Fetching historical market data...")
        try:
            all_data = dm.get_all_pairs()
            for symbol, df in all_data.items():
                if df is not None and not df.empty:
                    push_to_redis(r, symbol, df)
                else:
                    logging.warning(f"No historical data retrieved for {symbol}.")
        except Exception as e:
            logging.error(f"Error fetching historical data: {e}")
        time.sleep(POLL_INTERVAL)

def poll_live_data(r, dm):
    while True:
        try:
            all_data = dm.get_all_live_pairs()
            for symbol, df in all_data.items():
                if df is not None and not df.empty:
                    # Push live rolling window to a separate key
                    data_json = df.reset_index().to_json(orient="records", date_format="iso")
                    r.set(f"live_price:{symbol}", data_json)
        except Exception as e:
            logging.error(f"Error fetching live data: {e}")
        time.sleep(15) # Fast polling every 15 seconds

def run_service():
    logging.info(f"Starting Data Ingestion Service. Connecting to {REDIS_URL}...")
    r = redis.Redis.from_url(REDIS_URL)
    dm = DataManager()
    
    t1 = threading.Thread(target=poll_historical_data, args=(r, dm), daemon=True)
    t2 = threading.Thread(target=poll_live_data, args=(r, dm), daemon=True)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

if __name__ == "__main__":
    run_service()
