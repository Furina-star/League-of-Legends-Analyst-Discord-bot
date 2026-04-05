import asyncio
import csv
import os, sys
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


async def mine_data(seed_game_name, seed_tag_line):
    client = RiotAPIClient(api_key=RIOT_KEY, default_platform=PLATFORM, default_region=REGION)

    # Set up the Database Tracker
    visited_matches = set()
    puuid_queue = []
    matches_collected = 0

    # Ensure the data folder exists
    os.makedirs("data", exist_ok=True)

    # Create CSV Headers if file doesn't exist
    if os.path.exists(CSV_FILENAME):
        print ("Found Existing CSV File! Loading Save State...")
        with open(CSV_FILENAME, mode='r', newline='') as file:
            reader = csv.reader(file)
            next(reader, None)
            for row in reader:
                if row:
                    visited_matches.add(row[0])
                    matches_collected += 1
        print(f"Resuming from {matches_collected} matches...")
    # Create CSV Headers if file doesn't exist
    else:
        with open(CSV_FILENAME, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "matchId", "blueTop", "blueJungle", "blueMid", "blueADC", "blueSupport",
                "redTop", "redJungle", "redMid", "redADC", "redSupport",
                "blueWin"
            ])

    if matches_collected >= TARGET_MATCHES:
        print("🎯 Target already reached! No mining needed.")
        return

    # Get the Seed PUUID
    print(f"🌱 Planting seed: {seed_game_name}#{seed_tag_line}")
    seed_puuid = await client.get_puuid(seed_game_name, seed_tag_line)
    if not seed_puuid:
        print("❌ Invalid Seed Player.")
        return

    puuid_queue.append(seed_puuid)

    # Rebuild the spider web on resume
    if matches_collected > 0:
        print("⚡ Save state detected. Force-fetching seed's latest match to rebuild the player queue...")
        seed_history = await client.get_match_history(seed_puuid, count=1)

        if seed_history:
            jumpstart_match = await client.get_match_details(seed_history[0])
            await asyncio.sleep(1.2)  # Rate limit safety

            if jumpstart_match and 'info' in jumpstart_match:
                for p in jumpstart_match['info']['participants']:
                    if p['puuid'] not in puuid_queue:
                        puuid_queue.append(p['puuid'])

        print(f"🕸️ Web restored! Found {len(puuid_queue)} new players to branch out to.")

    # The Infinite Spider Loop
    while puuid_queue and matches_collected < TARGET_MATCHES:
        current_puuid = puuid_queue.pop(0)
        print(f"\n🔍 Scanning new player... (Queue size: {len(puuid_queue)})")

        # Get their last 20 Ranked games
        match_history = await client.get_match_history(current_puuid, count=20)
        if not match_history:
            continue

        for match_id in match_history:
            if match_id in visited_matches or matches_collected >= TARGET_MATCHES:
                continue

            visited_matches.add(match_id)
            match_data = await client.get_match_details(match_id)

            # Rate limit safety delay (1.2s = ~50 requests per minute)
            await asyncio.sleep(1.2)

            if not match_data or 'info' not in match_data:
                continue

            participants = match_data['info']['participants']

            # Add all 10 players to the queue to scan them later!
            for p in participants:
                if p['puuid'] not in puuid_queue:
                    puuid_queue.append(p['puuid'])

            # Data Extraction (The magic part)
            draft = {"blue": {}, "red": {}}
            blue_win = 0

            # Match V5 already tells us their role! No sorter needed!
            for p in participants:
                team = "blue" if p['teamId'] == 100 else "red"
                role = p['teamPosition']  # TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY
                c_name = p['championName']

                # Sometimes Riot returns "Invalid" roles for remakes/AFKs.
                if role not in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
                    break

                draft[team][role] = c_name

                if team == "blue":
                    blue_win = 1 if p['win'] else 0

            # If the draft dictionary is fully populated (all 10 roles exist)
            if len(draft["blue"]) == 5 and len(draft["red"]) == 5:
                row = [
                    match_id,
                    draft["blue"]["TOP"], draft["blue"]["JUNGLE"], draft["blue"]["MIDDLE"], draft["blue"]["BOTTOM"],
                    draft["blue"]["UTILITY"],
                    draft["red"]["TOP"], draft["red"]["JUNGLE"], draft["red"]["MIDDLE"], draft["red"]["BOTTOM"],
                    draft["red"]["UTILITY"],
                    blue_win
                ]

                # Append row to CSV instantly
                with open(CSV_FILENAME, mode='a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(row)

                matches_collected += 1
                print(f"✅ Saved Match {matches_collected}/{TARGET_MATCHES} [{match_id}]")

    print("\n🎉 DATA MINING COMPLETE!")

# Run the async loop
if __name__ == "__main__":
    # Can change the seed player to anyone, Just make sure they have a lot of ranked games for better results.
    asyncio.run(mine_data("Hide on Bush", "KR1"))