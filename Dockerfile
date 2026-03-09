FROM python:3.11-slim

WORKDIR /app

# System deps for BeautifulSoup lxml parser (optional, falls back to html.parser)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Runtime data directories
RUN mkdir -p data/conversations data/builds data/settings data/confluence uploads

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
