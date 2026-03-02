FROM python:3.11-slim

# System deps + Node.js 18 (required by Reflex to build the React frontend)
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl unzip ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

RUN chmod +x /app/entrypoint.sh

# Reflex frontend (Next.js) on 3000, backend (FastAPI) on 8000
EXPOSE 3000 8000

ENTRYPOINT ["/app/entrypoint.sh"]
