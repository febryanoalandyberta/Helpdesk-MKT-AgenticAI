import asyncio
import aiohttp
import os
import json

async def main():
    bot_token = "8494195461:AAEhUFmfMi3WvUXK5oTtCJpib_NK90zwJqg"
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"timeout": 5}, timeout=10) as resp:
            print(f"Status: {resp.status}")
            data = await resp.json()
            print(json.dumps(data, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
