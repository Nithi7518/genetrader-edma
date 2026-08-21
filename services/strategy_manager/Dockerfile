FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi uvicorn

# Copy shared config
COPY shared/ ./shared/

# Copy necessary compute engine components for strategy types
COPY services/compute_engine/ ./services/compute_engine/

# Copy strategy manager service
COPY services/strategy_manager/ ./services/strategy_manager/

ENV PYTHONPATH=/app
EXPOSE 8001
CMD ["uvicorn", "services.strategy_manager.main:app", "--host", "0.0.0.0", "--port", "8001"]
