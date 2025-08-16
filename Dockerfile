FROM python:3.11-slim

WORKDIR /app

# Copy proxy code
COPY redis-proxy.py .

# Use unbuffered output (so logs show up right away in docker logs)
ENV PYTHONUNBUFFERED=1

CMD ["python", "redis-proxy.py"]
