"""
Redis Proxy Server

A transparent proxy that allows local Redis clients to connect to a Redis Cloud instance
without having to handle authentication themselves.

The proxy:
- Listens on localhost:6379 (standard Redis port)
- Accepts client connections and forwards them to a provided external Redis server
- Automatically handles AUTH commands using configured credentials
- Provides transparent bidirectional data piping between client and server

Usage:
    python redis-proxy.py

Environment variables:
    REDIS_HOST: Redis server hostname
    REDIS_PORT: Redis server port
    REDIS_USER: Redis username
    REDIS_PASS: Redis password
"""

import os
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_USER = os.getenv("REDIS_USER")
REDIS_PASS = os.getenv("REDIS_PASS")

if not REDIS_PASS:
  logging.error("CRITICAL: REDIS_PASS is missing!")
  exit(1)


async def pipe(reader, writer):
  """Handles bidirectional data flow and closes cleanly on error"""
  try:
    while True:
      data = await reader.read(8192)  # 8KB Buffer
      if not data:
        break
      writer.write(data)
      await writer.drain()
  except Exception:
    pass
  finally:
    try:
      writer.close()
    except:
      pass


async def handle_client(client_reader, client_writer):
  peer = client_writer.get_extra_info('peername')

  # --- STEP A: FILTER HEALTHCHECKS (The "Security Attack" Fix) ---
  try:
    # Peek at the first byte to see if it's HTTP (G=GET, P=POST, H=HEAD)
    first_byte = await client_reader.read(1)

    if not first_byte:
      client_writer.close()
      return

    if first_byte in [b'G', b'P', b'H', b'O', b'D']:
      logging.warning(f"Ignored HTTP Healthcheck from {peer}")
      client_writer.close()
      return

  except Exception:
    client_writer.close()
    return

  # --- STEP B: CONNECT UPSTREAM ---
  try:
    server_reader, server_writer = await asyncio.open_connection(REDIS_HOST, REDIS_PORT)
  except Exception as e:
    logging.error(f"Upstream Connect Failed ({REDIS_HOST}:{REDIS_PORT}): {e}")
    client_writer.close()
    return

  # --- STEP C: AUTHENTICATE ---
  try:
    # Reconstruct Redis AUTH command
    auth_payload = f"*3\r\n$4\r\nAUTH\r\n${len(REDIS_USER)}\r\n{REDIS_USER}\r\n${len(REDIS_PASS)}\r\n{REDIS_PASS}\r\n"
    server_writer.write(auth_payload.encode())
    await server_writer.drain()

    # Consume the response (+OK) so the client doesn't see it
    await server_reader.readuntil(b"\r\n")

  except Exception as e:
    logging.error(f"Auth Handshake Failed: {e}")
    client_writer.close()
    if server_writer:
      server_writer.close()
    return

  # --- STEP D: START PIPING ---
  # Forward that first byte we peeked at earlier
  server_writer.write(first_byte)

  await asyncio.gather(
      pipe(client_reader, server_writer),
      pipe(server_reader, client_writer),
  )


async def main():
  server = await asyncio.start_server(handle_client, "0.0.0.0", 6379)
  logging.info(f"Proxy Online -> {REDIS_HOST}:{REDIS_PORT}")
  async with server:
    await server.serve_forever()

if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    pass
