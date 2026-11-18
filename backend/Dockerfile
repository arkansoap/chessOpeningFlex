FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Engine for the batch analysis: the official release where one exists for
# the platform (Linux x86-64), the distribution package otherwise.
RUN python scripts/fetch_stockfish.py \
    || (apt-get update \
        && apt-get install -y --no-install-recommends stockfish \
        && rm -rf /var/lib/apt/lists/* \
        && ln -sf /usr/games/stockfish /usr/local/bin/stockfish)

ENV PYTHONPATH=/app \
    DATABASE_URL=sqlite:////data/chessopeningflex.db \
    DATA_DIR=/data
VOLUME /data
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
