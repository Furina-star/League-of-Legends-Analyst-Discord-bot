"""
data_miner.py
Hardened Spider Web Miner designed specifically for the 32-Feature ML Model.
Outputs directly to upgraded_drafts.csv with multi-day stability protocols.
"""
import asyncio
import aiohttp
import csv
import os
import sys
import aiofiles
import pandas as pd
from collections import deque
from dotenv import load_dotenv
from services.riot_api import RiotAPIClient

load_dotenv()
RIOT_KEY = os.getenv('RIOT_API_KEY')
if not RIOT_KEY:
    sys.exit("Error: RIOT_API_KEY must be set in the .env file.")

REGION = "europe"
PLATFORM = "euw1"
TARGET_MATCHES = 50000
RATE_LIMIT_DELAY = 1.25

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
CSV_FILENAME = str(os.path.join(SCRIPT_DIR, "../data", "training", "upgraded_drafts.csv"))

if os.path.exists(CSV_FILENAME):
    df = pd.read_csv(CSV_FILENAME, low_memory=False)
    assert isinstance(df, pd.DataFrame)
    current_rows = len(df)
    print(f"Found {current_rows} matches. Auto-mining until {TARGET_MATCHES}...")
    del df # Free memory immediately
else:
    print(f"No database found. Starting fresh and mining {TARGET_MATCHES} matches...")

async def _load_existing_csv():
    visited_matches = set()
    matches_collected = 0

    if not os.path.exists(CSV_FILENAME):
        return visited_matches, matches_collected

    print("Found Existing CSV File! Loading Save State...")
    async with aiofiles.open(CSV_FILENAME, mode='r', newline='') as file:
        content = await file.read()
        reader = csv.reader(content.splitlines())
        next(reader, None)
        for row in reader:
            if row:
                visited_matches.add(row[0])
                matches_collected += 1

    print(f"Resuming from {matches_collected} matches...")
    return visited_matches, matches_collected

async def _create_csv_headers():
    async with aiofiles.open(CSV_FILENAME, mode='w', newline='') as file:
        headers = (
            "matchId,blueTop,blueJungle,blueMid,blueADC,blueSupport,"
            "redTop,redJungle,redMid,redADC,redSupport,blueWin,"
            "blueTopMastery,blueTopRank,blueJungleMastery,blueJungleRank,"
            "blueMidMastery,blueMidRank,blueADCMastery,blueADCRank,blueSupportMastery,blueSupportRank,"
            "redTopMastery,redTopRank,redJungleMastery,redJungleRank,"
            "redMidMastery,redMidRank,redADCMastery,redADCRank,redSupportMastery,redSupportRank\n"
        )
        await file.write(headers)

async def _rebuild_queue(client, seed_puuid):
    puuid_queue = deque([seed_puuid])
    seen_puuids = {seed_puuid}

    print("Save state detected. Force-fetching seed's latest match to rebuild the player queue...")

    try:
        seed_history = await client.get_match_history(seed_puuid, count=1)
        await asyncio.sleep(RATE_LIMIT_DELAY) # PACING

        if seed_history:
            jumpstart_match = await client.get_match_details(seed_history[0])
            await asyncio.sleep(RATE_LIMIT_DELAY) # PACING

            if jumpstart_match and 'info' in jumpstart_match:
                for p in jumpstart_match['info']['participants']:
                    puuid = p['puuid']
                    if puuid not in seen_puuids:
                        puuid_queue.append(puuid)
                        seen_puuids.add(puuid)
    except Exception as e:
        print(f"⚠️ Failed to rebuild from seed: {e}")

    print(f"Web Restored! Found {len(puuid_queue)} new players to branch out to.")
    return puuid_queue, seen_puuids

def _parse_draft(participants):
    draft = {"blue": {}, "red": {}}
    blue_win = 0

    for p in participants:
        team = "blue" if p['teamId'] == 100 else "red"
        role = p['teamPosition']

        if role not in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
            return None, "invalid_role"

        draft[team][role] = {
            "championName": p['championName'],
            "championId": p['championId'],
            "puuid": p['puuid'],
            "summonerId": p.get('summonerId', '')
        }

        if team == "blue":
            blue_win = 1 if p.get('win', False) else 0

    if len(draft["blue"]) == 5 and len(draft["red"]) == 5:
        return draft, blue_win

    return None, "incomplete_draft"

def _parse_rank_string(rank_str: str) -> float:
    if not rank_str or "Unranked" in rank_str:
        return 3.0

    upper_str = rank_str.upper()
    rank_map = {
        "IRON": 0.0, "BRONZE": 1.0, "SILVER": 2.0, "GOLD": 3.0,
        "PLATINUM": 4.0, "EMERALD": 5.0, "DIAMOND": 6.0,
        "MASTER": 7.0, "GRANDMASTER": 8.0, "CHALLENGER": 9.0
    }

    for tier, val in rank_map.items():
        if tier in upper_str:
            return val

    return 3.0

async def _fetch_player_stats(client, player_data):
    # Mastery Call
    try:
        mastery = await client.get_champion_mastery(player_data['puuid'], player_data['championId'])
    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, TypeError):
        mastery = 0.0
    await asyncio.sleep(RATE_LIMIT_DELAY) # PACING

    # Rank Call
    try:
        rank_str = await client.get_summoner_rank(player_data['puuid'])
        rank_val = _parse_rank_string(rank_str)
    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, TypeError, ValueError):
        rank_val = 3.0
    await asyncio.sleep(RATE_LIMIT_DELAY) # PACING

    return float(mastery), float(rank_val)

async def _append_row(match_id, draft, blue_win, stats):
    row = [
        match_id,
        draft["blue"]["TOP"]["championName"], draft["blue"]["JUNGLE"]["championName"],
        draft["blue"]["MIDDLE"]["championName"], draft["blue"]["BOTTOM"]["championName"], draft["blue"]["UTILITY"]["championName"],
        draft["red"]["TOP"]["championName"], draft["red"]["JUNGLE"]["championName"],
        draft["red"]["MIDDLE"]["championName"], draft["red"]["BOTTOM"]["championName"], draft["red"]["UTILITY"]["championName"],
        blue_win,
        stats["blue"]["TOP"]["mastery"], stats["blue"]["TOP"]["rank"],
        stats["blue"]["JUNGLE"]["mastery"], stats["blue"]["JUNGLE"]["rank"],
        stats["blue"]["MIDDLE"]["mastery"], stats["blue"]["MIDDLE"]["rank"],
        stats["blue"]["BOTTOM"]["mastery"], stats["blue"]["BOTTOM"]["rank"],
        stats["blue"]["UTILITY"]["mastery"], stats["blue"]["UTILITY"]["rank"],
        stats["red"]["TOP"]["mastery"], stats["red"]["TOP"]["rank"],
        stats["red"]["JUNGLE"]["mastery"], stats["red"]["JUNGLE"]["rank"],
        stats["red"]["MIDDLE"]["mastery"], stats["red"]["MIDDLE"]["rank"],
        stats["red"]["BOTTOM"]["mastery"], stats["red"]["BOTTOM"]["rank"],
        stats["red"]["UTILITY"]["mastery"], stats["red"]["UTILITY"]["rank"]
    ]
    async with aiofiles.open(CSV_FILENAME, mode='a', newline='') as file:
        await file.write(",".join(str(x) for x in row) + "\n")

async def _save_if_new(match_id, participants, visited_matches, matches_collected, client):
    visited_matches.add(match_id)
    parsed = _parse_draft(participants)
    if parsed is None or parsed[0] is None:
        return matches_collected

    draft, blue_win = parsed
    stats = {"blue": {}, "red": {}}

    for team in ["blue", "red"]:
        for role in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
            mastery, rank = await _fetch_player_stats(client, draft[team][role])
            stats[team][role] = {"mastery": mastery, "rank": rank}

    await _append_row(match_id, draft, blue_win, stats)
    matches_collected += 1
    print(f"✅ Saved Match {matches_collected}/{TARGET_MATCHES} [{match_id}]")
    return matches_collected

async def _process_single_match(client, match_id, visited_matches, puuid_queue, seen_puuids, matches_collected):
    try:
        match_data = await client.get_match_details(match_id)
        await asyncio.sleep(RATE_LIMIT_DELAY) # PACING

        if not match_data or 'info' not in match_data:
            return matches_collected

        participants = match_data['info']['participants']

        for p in participants:
            puuid = p.get('puuid')
            if puuid and puuid not in seen_puuids:
                puuid_queue.append(puuid)
                seen_puuids.add(puuid)

        return await _save_if_new(match_id, participants, visited_matches, matches_collected, client)

    except Exception as e:
        print(f"⚠️ Failed to process match {match_id}. Skipping. Error: {e}")
        return matches_collected

async def _process_match_history(client, match_history, visited_matches, puuid_queue, seen_puuids, matches_collected):
    for match_id in match_history:
        if matches_collected >= TARGET_MATCHES:
            break

        if match_id in visited_matches:
            continue

        matches_collected = await _process_single_match(
            client, match_id, visited_matches, puuid_queue, seen_puuids, matches_collected
        )

    return matches_collected

async def _replenish_queue_if_empty(client, puuid_queue, seen_puuids):
    if puuid_queue:
        return True

    print("🕸️ Spider hit a dead end. Fetching Challenger Ladder to jumpstart...")
    try:
        ladder = await client.get_challenger_ladder(queue="RANKED_SOLO_5x5")
        await asyncio.sleep(RATE_LIMIT_DELAY)

        for entry in ladder[:50]:
            pid = await client.get_puuid_by_summoner_id(entry['summonerId'])
            await asyncio.sleep(RATE_LIMIT_DELAY)

            if pid and pid not in seen_puuids:
                puuid_queue.append(pid)
                seen_puuids.add(pid)
    except Exception as e:
        print(f"⚠️ Ladder fetch failed: {e}")

    if not puuid_queue:
        print("❌ Failsafe failed. Riot API might be down.")
        return False

    return True

async def _initialize_miner_state():
    os.makedirs(os.path.dirname(CSV_FILENAME), exist_ok=True)
    visited_matches, matches_collected = await _load_existing_csv()

    if not os.path.exists(CSV_FILENAME):
        await _create_csv_headers()

    return visited_matches, matches_collected

async def _initialize_spider_queue(client, seed_game_name, seed_tag_line, matches_collected):
    print(f"🌱 Planting seed: {seed_game_name}#{seed_tag_line}")
    # Strictly named seed_puuid
    seed_puuid = await client.get_puuid(seed_game_name, seed_tag_line)
    await asyncio.sleep(RATE_LIMIT_DELAY) # PACING

    if matches_collected > 0 and seed_puuid:
        return await _rebuild_queue(client, seed_puuid)
    elif seed_puuid:
        return deque([seed_puuid]), {seed_puuid}

    print("❌ Invalid Seed Player. Attempting to start from Challenger Ladder...")
    return deque(), set()

async def _run_spider_loop(client, puuid_queue, seen_puuids, visited_matches, matches_collected):
    stop_event = asyncio.Event()
    try:
        while not stop_event.is_set():
            if not await _replenish_queue_if_empty(client, puuid_queue, seen_puuids):
                break

            if len(seen_puuids) > 100000:
                print("🧹 Memory limit reached. Flushing PUUID tracking cache...")
                seen_puuids.clear()

            # Strictly named current_puuid
            current_puuid = puuid_queue.popleft()
            print(f"\n🔍 Scanning new player... (Queue size: {len(puuid_queue)})")

            try:
                # Safely passing current_puuid to the API
                match_history = await client.get_match_history(current_puuid, count=20)
                await asyncio.sleep(RATE_LIMIT_DELAY) # PACING
            except Exception as e:
                print(f"⚠️ Failed to fetch history for player. Error: {e}")
                continue

            if not match_history:
                continue

            matches_collected = await _process_match_history(
                client, match_history, visited_matches, puuid_queue, seen_puuids, matches_collected
            )

            if matches_collected >= TARGET_MATCHES:
                stop_event.set()
                print("\n🎉 DATA MINING COMPLETE!")

    except asyncio.CancelledError:
        print("\n🛑 Mining process forcefully cancelled.")
        raise
    return matches_collected

async def mine_data(seed_game_name, seed_tag_line):
    client = RiotAPIClient(api_key=RIOT_KEY, default_platform=PLATFORM, default_region=REGION)
    await client.setup_cache()

    matches_collected = 0
    try:
        visited_matches, matches_collected = await _initialize_miner_state()

        if matches_collected >= TARGET_MATCHES:
            print("🎯 Target already reached! No mining needed.")
            return

        puuid_queue, seen_puuids = await _initialize_spider_queue(
            client, seed_game_name, seed_tag_line, matches_collected
        )

        matches_collected = await _run_spider_loop(
            client, puuid_queue, seen_puuids, visited_matches, matches_collected
        )

    finally:
        print(f"\n💾 Shutting down safely. Total matches preserved: {matches_collected}")
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(mine_data("NattyNatt", "2005"))
    except KeyboardInterrupt:
        print("\n🛑 Execution Interrupted by User (Ctrl+C). Terminated Safely.")
        sys.exit(0)