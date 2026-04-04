import asyncio
import csv
import os
from dotenv import load_dotenv
from riot_api import RiotAPIClient

# --- CONFIGURATION ---

load_dotenv()
RIOT_KEY = os.getenv('RIOT_API_KEY')
REGION = "asia"  # Change region
PLATFORM = "sg2"  # Change platform (e.g., "na1", "euw1", "kr1", etc.)
TARGET_MATCHES = 1000  # How many games to mine
CSV_FILENAME = "../ranked_drafts.csv"


async def mine_data(seed_game_name, seed_tag_line):
    client = RiotAPIClient(api_key=RIOT_KEY, default_platform=PLATFORM, default_region=REGION)

    # Setup the Database Tracker
    visited_matches = set()
    puuid_queue = []
    matches_collected = 0

    # Ensure the data folder exists
    os.makedirs("..", exist_ok=True)

    # Create CSV Headers if file doesn't exist
    if not os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "blueTop", "blueJungle", "blueMid", "blueADC", "blueSupport",
                "redTop", "redJungle", "redMid", "redADC", "redSupport",
                "blueWin"  # 1 if Blue won, 0 if Red won
            ])

    # Get the Seed PUUID
    print(f"🌱 Planting seed: {seed_game_name}#{seed_tag_line}")
    seed_puuid = await client.get_puuid(seed_game_name, seed_tag_line)
    if not seed_puuid:
        print("❌ Invalid Seed Player.")
        return

    puuid_queue.append(seed_puuid)

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
    asyncio.run(mine_data("Hide on bush", "KR1"))