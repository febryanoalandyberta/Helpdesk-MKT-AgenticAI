import asyncio
import aiohttp
import os
import sys

async def main():
    bot_token = "8494195461:AAEhUFmfMi3WvUXK5oTtCJpib_NK90zwJqg"
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    print(f"Calling {url}")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"offset": 0, "timeout": 5}, timeout=10) as resp:
            print(f"Status: {resp.status}")
            print(await resp.text())

if __name__ == "__main__":
    asyncio.run(main())
