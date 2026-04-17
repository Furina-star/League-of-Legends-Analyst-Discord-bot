import aiosqlite
import asyncio
import os
from dotenv import load_dotenv
from riot_api import RiotAPIClient

load_dotenv()

# A curated list of top-tier accounts to harvest data from.
# You can expand this list with any Riot IDs you want.
TARGETS = [
    ("Hide on bush", "KR1", "kr"),  # Faker
    ("T1 Gumayusi", "KR1", "kr"),
    ("T1 Keria", "KR1", "kr"),
    ("Canyon", "KR1", "kr"),
    ("Chovy", "KR1", "kr")
]


async def inject_queue():
    riot = RiotAPIClient(os.getenv("RIOT_API_KEY"))
    total_injected = 0

    print("Starting High-Elo Data Injection...")

    # Connect directly to the bot's database
    async with aiosqlite.connect("data/server_state.db") as conn:
        for game_name, tag_line, server in TARGETS:
            print(f"Harvesting {game_name}...")

            # 1. Resolve PUUID
            puuid = await riot.get_puuid(game_name, tag_line, server)
            if not puuid:
                print(f"Could not find {game_name}.")
                continue

            # 2. Rip their last 100 matches
            matches = await riot.get_match_history(puuid, count=100, server_context=server)
            if not matches:
                continue

            # 3. Inject directly into the passive miner queue
            for match_id in matches:
                # INSERT OR IGNORE prevents duplicate matches from crashing the DB
                await conn.execute("INSERT OR IGNORE INTO ml_queue (match_id, server) VALUES (?, ?)",
                                   (match_id, server))
                total_injected += 1

            await conn.commit()
            await asyncio.sleep(1)  # Micro-pause to respect rate limits

    print(f"\nInjection Complete! Dropped {total_injected} matches into the AI queue.")


if __name__ == "__main__":
    asyncio.run(inject_queue())