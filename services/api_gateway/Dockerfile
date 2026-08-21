FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi uvicorn celery redis

# Copy shared config
COPY shared/ ./shared/

# Copy necessary compute engine components for Celery task definitions
COPY services/compute_engine/ ./services/compute_engine/

# Copy API Gateway service
COPY services/api_gateway/ ./services/api_gateway/

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
