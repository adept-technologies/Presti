import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

SMARTLEAD_API_KEY = os.getenv("SMARTLEAD_API_KEY")
EMAIL_ACCOUNT_ID = os.getenv("SMARTLEAD_EMAIL_ACCOUNT_ID")

params = {"api_key": SMARTLEAD_API_KEY}
WARMUP_STATS_URL = (
    f"https://server.smartlead.ai/api/v1/email-accounts/{EMAIL_ACCOUNT_ID}/warmup-stats"
)


async def get_warmup_stats():
    async with httpx.AsyncClient() as client:
        response = await client.get(url=WARMUP_STATS_URL, params=params)

        response.raise_for_status()

        return response.json()

if __name__ == "__main__":
    async def main():
        x = await get_warmup_stats()
        print(x)

    asyncio.run(main())