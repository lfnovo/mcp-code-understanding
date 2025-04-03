"""
Entry point for the Code Understanding MCP Server.
"""
import asyncio
from pathlib import Path

from .server import CodeUnderstandingServer

async def main():
    server = CodeUnderstandingServer()
    try:
        await server.start()
        # Keep the server running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
