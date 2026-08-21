FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt redis

# Copy shared config
COPY shared/ ./shared/

# Copy data ingestion service
COPY services/data_ingestion/ ./services/data_ingestion/

ENV PYTHONPATH=/app
CMD ["python", "services/data_ingestion/service.py"]
