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

import os, asyncio

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_USER = os.getenv("REDIS_USER")
REDIS_PASS = os.getenv("REDIS_PASS")

# Validate all required environment variables are set
required_vars = {
    "REDIS_HOST": REDIS_HOST,
    "REDIS_PORT": REDIS_PORT,
    "REDIS_USER": REDIS_USER,
    "REDIS_PASS": REDIS_PASS
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    raise EnvironmentError(f"Required environment variables not set: {', '.join(missing_vars)}")

REDIS_PORT = int(REDIS_PORT)

async def handle_client(client_reader, client_writer):
    # Connect to real Redis
    try:
        server_reader, server_writer = await asyncio.open_connection(REDIS_HOST, REDIS_PORT)
    except Exception as e:
        print(f"Upstream connection failed: {e}")
        client_writer.close()
        return

    # Send AUTH right away
    auth_cmd = f"*3\r\n$4\r\nAUTH\r\n${len(REDIS_USER)}\r\n{REDIS_USER}\r\n${len(REDIS_PASS)}\r\n{REDIS_PASS}\r\n"
    server_writer.write(auth_cmd.encode())
    await server_writer.drain()

    # Read and discard AUTH response (don’t forward to client)
    await server_reader.readuntil(b"\r\n")

    async def pipe(reader, writer):
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()

    # Pipe client→server and server→client concurrently
    await asyncio.gather(
        pipe(client_reader, server_writer),
        pipe(server_reader, client_writer),
    )

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 6379)
    print("Proxy listening on port 6379...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
