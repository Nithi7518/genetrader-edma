import logging
from celery import shared_task
from .ga_optimizer import GAOptimizer
from .evaluator import Evaluator

import os
import redis
import pandas as pd
import json

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

def _get_redis_data():
    from shared.config import TRADING_PAIRS
    r = redis.Redis.from_url(REDIS_URL)
    data_cache = {}
    for pair in TRADING_PAIRS:
        raw = r.get(f"ohlcv:{pair}")
        if raw:
            df = pd.read_json(raw, orient="records")
            if "Date" in df.columns:
                df.set_index("Date", inplace=True)
            data_cache[pair] = df
    return data_cache

@shared_task(bind=True)
def run_optimization_task(self):
    """
    Celery task that runs the Genetic Algorithm.
    It will update its state so the FastAPI gateway can read progress.
    """
    logging.info("Starting GA Optimization Task...")
    
    # 1. Load Data
    data_cache = _get_redis_data()
    evaluator = Evaluator(data_cache=data_cache)
    
    # 2. Run Optimizer
    optimizer = GAOptimizer(
        fitness_fn=evaluator.evaluate,
        n_processes=1 # Celery workers are already distributed, so internal multi-processing is set to 1
    )
    
    # We will modify the optimizer slightly later to update this Celery task's state per generation
    self.update_state(state='PROGRESS', meta={'generation': 0, 'status': 'Starting evolution'})
    
    best_chrom, evo_log = optimizer.run()
    
    logging.info("Optimization Task Complete.")
    
    return {
        "status": "COMPLETED",
        "best_chromosome": best_chrom,
        "evolution_log": evo_log
    }
