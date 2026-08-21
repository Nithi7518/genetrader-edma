FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt celery redis

# Copy shared config
COPY shared/ ./shared/

# Copy compute engine service
COPY services/compute_engine/ ./services/compute_engine/

# Run Celery worker
ENV PYTHONPATH=/app
CMD ["celery", "-A", "services.compute_engine.celery_app", "worker", "--loglevel=info"]
