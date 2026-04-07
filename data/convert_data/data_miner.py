import asyncio
import csv
import os, sys
import aiofiles
from dotenv import load_dotenv
from riot_api import RiotAPIClient

load_dotenv()
RIOT_KEY = os.getenv('RIOT_API_KEY')
if not RIOT_KEY: # Quick Sanity Check
    sys.exit("Error: DISCORD_TOKEN and RIOT_API_KEY must be set in the .env file.")

REGION = "asia"  # Change region
PLATFORM = "sg2"  # Change platform (e.g., "na1", "euw1", "kr1", etc.)
TARGET_MATCHES = 50000  # How many games to mine

# Use absolute path relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILENAME = os.path.join(SCRIPT_DIR, "..", "ranked_drafts.csv")

# Initialize reading existing csv dataset as a function
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

# Initialize the CSV Headers as a function
async def _create_csv_headers():
    async with aiofiles.open(CSV_FILENAME, mode='w', newline='') as file:
        content = "matchId,blueTop,blueJungle,blueMid,blueADC,blueSupport,redTop,redJungle,redMid,redADC,redSupport,blueWin\n"
        await file.write(content)

# Initialize Queue Rebuilder as a function
async def _rebuild_queue(client, seed_puuid):
    puuid_queue = [seed_puuid]
    print("Save state detected. Force-fetching seed's latest match to rebuild the player queue...")

    seed_history = await client.get_match_history(seed_puuid, count=1)
    if seed_history:
        jumpstart_match = await client.get_match_details(seed_history[0])
        await asyncio.sleep(1.2)

        if jumpstart_match and 'info' in jumpstart_match:
            for p in jumpstart_match['info']['participants']:
                if p['puuid'] not in puuid_queue:
                    puuid_queue.append(p['puuid'])

    print(f"Web Restored! Found {len(puuid_queue)} new players to branch out to.")
    return puuid_queue

# Extracts the draft and result from a match's participants. Returns (row, None) or (None, reason).
def _parse_draft(participants):
    draft = {"blue": {}, "red": {}}
    blue_win = 0

    for p in participants:
        team = "blue" if p['teamId'] == 100 else "red"
        role = p['teamPosition']
        c_name = p['championName']

        if role not in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
            return None, "invalid_role"

        draft[team][role] = c_name
        if team == "blue":
            blue_win = 1 if p['win'] else 0

    if len(draft["blue"]) == 5 and len(draft["red"]) == 5:
        return draft, blue_win

    return None, "incomplete_draft"

# Appends a single match row to the CSV file asynchronously
async def _append_row(match_id, draft, blue_win):
    row = [
        match_id,
        draft["blue"]["TOP"], draft["blue"]["JUNGLE"], draft["blue"]["MIDDLE"], draft["blue"]["BOTTOM"],
        draft["blue"]["UTILITY"],
        draft["red"]["TOP"], draft["red"]["JUNGLE"], draft["red"]["MIDDLE"], draft["red"]["BOTTOM"],
        draft["red"]["UTILITY"],
        blue_win
    ]
    async with aiofiles.open(CSV_FILENAME, mode='a', newline='') as file:
        await file.write(",".join(str(x) for x in row) + "\n")

# Saves match to CSV only if not already visited. Returns updated matches_collected.
async def _save_if_new(match_id, participants, visited_matches, matches_collected):
    visited_matches.add(match_id)
    draft, blue_win = _parse_draft(participants)
    if draft is None:
        return matches_collected

    await _append_row(match_id, draft, blue_win)
    matches_collected += 1
    print(f"✅ Saved Match {matches_collected}/{TARGET_MATCHES} [{match_id}]")
    return matches_collected

# Processes a list of match IDs, saves valid ones, and returns updated matches_collected.
async def _process_match_history(client, match_history, visited_matches, puuid_queue, matches_collected):
    for match_id in match_history:
        if matches_collected >= TARGET_MATCHES:
            break

        if match_id in visited_matches:
            continue

        match_data = await client.get_match_details(match_id)
        await asyncio.sleep(1.2)

        if not match_data or 'info' not in match_data:
            continue

        participants = match_data['info']['participants']

        for p in participants:
            if p['puuid'] not in puuid_queue:
                puuid_queue.append(p['puuid'])

        matches_collected = await _save_if_new(match_id, participants, visited_matches, matches_collected)

    return matches_collected

# This is the main mining function that orchestrates the entire data collection process.
# It initializes the client, loads existing data, and runs the spider loop until the target number of matches is collected.
async def mine_data(seed_game_name, seed_tag_line):
    client = RiotAPIClient(api_key=RIOT_KEY, default_platform=PLATFORM, default_region=REGION)

    os.makedirs(os.path.dirname(CSV_FILENAME), exist_ok=True)
    visited_matches, matches_collected = await _load_existing_csv()

    if not os.path.exists(CSV_FILENAME):
        await _create_csv_headers()

    if matches_collected >= TARGET_MATCHES:
        print("🎯 Target already reached! No mining needed.")
        await client.close()
        return

    print(f"🌱 Planting seed: {seed_game_name}#{seed_tag_line}")
    seed_puuid = await client.get_puuid(seed_game_name, seed_tag_line)
    if not seed_puuid:
        print("❌ Invalid Seed Player.")
        await client.close()
        return

    if matches_collected > 0:
        puuid_queue = await _rebuild_queue(client, seed_puuid)
    else:
        puuid_queue = [seed_puuid]

    # Event-driven approach: the loop signals completion instead of sleeping to check a condition
    stop_event = asyncio.Event()

    async def spider_loop():
        nonlocal matches_collected
        while puuid_queue and not stop_event.is_set():
            current_puuid = puuid_queue.pop(0)
            print(f"\n🔍 Scanning new player... (Queue size: {len(puuid_queue)})")

            match_history = await client.get_match_history(current_puuid, count=20)
            if not match_history:
                continue

            matches_collected = await _process_match_history(
                client, match_history, visited_matches, puuid_queue, matches_collected
            )

            if matches_collected >= TARGET_MATCHES:
                stop_event.set()

        print("\n🎉 DATA MINING COMPLETE!")

    await spider_loop()
    await client.close()

if __name__ == "__main__":
    asyncio.run(mine_data("Hide on Bush", "KR1"))

