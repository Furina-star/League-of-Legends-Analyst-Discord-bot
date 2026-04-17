import pandas as pd
import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from riot_api import RiotAPIClient

load_dotenv()

RANK_WEIGHTS = {"IRON": 1, "BRONZE": 2, "SILVER": 3, "GOLD": 4, "PLATINUM": 5, "EMERALD": 6, "DIAMOND": 7, "MASTER": 8,
                "GRANDMASTER": 9, "CHALLENGER": 10}


async def fetch_player_stats_safe(riot, puuid, champ_id, server, retries=3):
    for attempt in range(retries):
        try:
            # Awaiting sequentially instead of gathering to prevent 10054 Connection Resets
            mastery = await riot.get_champion_mastery(puuid, champ_id, platform_override=server)
            rank_str = await riot.get_summoner_rank(puuid, platform_override=server)

            rank_val = RANK_WEIGHTS.get(rank_str.upper().split()[0], 3) if rank_str else 3
            return mastery, rank_val

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            print(f"⚠️ Connection dropped on player (Attempt {attempt + 1}/{retries}). Sleeping 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
            await asyncio.sleep(5)

    # Failsafe so the script never hard crashes on a dead account
    return 0, 3


async def retrofit_dataset():
    riot = RiotAPIClient(os.getenv("RIOT_API_KEY"))
    df = pd.read_csv("data/ranked_drafts.csv")

    df_mvp = df.head(1000).copy()
    print(f"Starting stable retrofit for {len(df_mvp)} matches...")

    for index, row in df_mvp.iterrows():
        # RESUME FEATURE: Skip matches that already successfully retrofitted before a crash
        if 'blueTopMastery' in df_mvp.columns and pd.notna(row.get('blueTopMastery')):
            continue

        match_id = row['matchId']
        server = match_id.split('_')[0].lower()

        try:
            match_data = await riot.get_match_details(match_id, server_context=server)
            participants = match_data.get('info', {}).get('participants', [])

            if len(participants) != 10:
                continue

            results = []
            # Loop sequentially rather than firing 20 requests instantly
            for p in participants:
                stats = await fetch_player_stats_safe(riot, p['puuid'], p['championId'], server)
                results.append(stats)
                await asyncio.sleep(0.1)  # Tiny micro-pause to keep the network pool clean

            roles = ['Top', 'Jungle', 'Mid', 'ADC', 'Support']
            for i in range(10):
                team_prefix = 'blue' if i < 5 else 'red'
                role = roles[i % 5]
                mastery, rank = results[i]
                df_mvp.at[index, f'{team_prefix}{role}Mastery'] = mastery
                df_mvp.at[index, f'{team_prefix}{role}Rank'] = rank

            print(f"[{index}/5000] Successfully retrofitted {match_id}")

            # Save more aggressively (every 10 matches)
            if index % 10 == 0:
                df_mvp.to_csv("data/upgraded_drafts.csv", index=False)

        except Exception as e:
            print(f"Match-level error on {match_id}: {e}")
            await asyncio.sleep(10)

    df_mvp.to_csv("data/upgraded_drafts.csv", index=False)
    print("MVP Dataset Complete.")


if __name__ == "__main__":
    asyncio.run(retrofit_dataset())