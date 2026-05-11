FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir mcp fastmcp pymongo
COPY . .
