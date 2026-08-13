FROM python:3.12-slim

WORKDIR /app

# System deps: stockfish binary for analysis, gcc for any compiled wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
