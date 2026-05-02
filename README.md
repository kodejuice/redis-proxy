# redis-proxy

## Overview

This image provides a lightweight **Redis authentication proxy**.
It exposes a local Redis-compatible endpoint (default port `6379`) and transparently forwards traffic to an external Redis server such as **Redis Cloud**.

The proxy automatically sends the `AUTH` command upstream using credentials from environment variables, so clients can connect **without handling passwords directly**.

---

## How to run

```bash
docker run -d \
  -p 6379:6379 \
  -e REDIS_HOST=your.redis.host \
  -e REDIS_PORT=12345 \
  -e REDIS_USER=default \
  -e REDIS_PASS=yourpassword \
  sochimab/redis-proxy:latest
```

Once running, you can connect using a standard Redis client:

```bash
redis-cli -h 127.0.0.1 -p 6379 ping
# -> PONG
```

---


## Use cases

* Drop-in replacement for `redis:alpine` in development or containerized stacks.
* Provide a local Redis endpoint even when the actual server is remote.

### Why?

I built this as a fix to an issue with self-hosted [`Appwrite`](https://appwrite.io) where you the Redis server you set must not be password authenticated

```yml
  # A custom redis-proxy, this is to get around an appwrite bug that 
  # required that our redis server be without AUTH
  # Our redis-proxy connects to our redis server with AUTH
  # then exposes a redis port that has no AUTH 
  redis:
    image: sochimab/redis-proxy:latest
    container_name: appwrite-redis
    <<: *x-logging
    restart: unless-stopped
    networks:
      - appwrite
    environment:
      - REDIS_HOST=${_CUSTOM_REDIS_HOST}
      - REDIS_PORT=${_CUSTOM_REDIS_PORT}
      - REDIS_USER=${_CUSTOM_REDIS_USERNAME}
      - REDIS_PASS=${_CUSTOM_REDIS_PASSWORD}
```

