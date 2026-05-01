FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir mcp fastmcp pymongo
COPY . .
ENTRYPOINT ["python", "-u"]
