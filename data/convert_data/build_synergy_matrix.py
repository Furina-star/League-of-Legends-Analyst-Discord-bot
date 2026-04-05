import pandas as pd
import json
import os
from itertools import combinations

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(SCRIPT_DIR)
CSV_PATH = os.path.join(DATA_DIR, "ranked_drafts.csv")
JSON_PATH = os.path.join(DATA_DIR, "Synergy_Matrix.json")

def build_synergy_matrix():
    print(f"Reading match data from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)

    synergy_data = {}

    # Define the columns for blue and red teams
    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    for index, row in df.iterrows():
        # Determine who won
        blue_won = row['blueWin'] == 1

        # Get the lists of champions for this specific match
        blue_champs = sorted([str(row[col]) for  col in blue_cols])
        red_champs = sorted([str(row[col]) for col in red_cols])

        # Generate every ducking possible synergies out there for blue team
        for duo in combinations(blue_champs, 2):
            pair_key = f"{duo[0]}-{duo[1]}"
            if pair_key not in synergy_data:
                synergy_data[pair_key] = {"wins": 0, "games": 0}

            synergy_data[pair_key]["games"] += 1
            if blue_won:
                synergy_data[pair_key]["wins"] += 1

        # Generate the same thing for red team
        for duo in combinations(red_champs, 2):
            pair_key = f"{duo[0]}-{duo[1]}"
            if pair_key not in synergy_data:
                synergy_data[pair_key] = {"wins": 0, "games": 0}

            synergy_data[pair_key]["games"] += 1
            if not blue_won:
                synergy_data[pair_key]["wins"] += 1

    # Calculate win rates and filter out the noises
    final_matrix = {}
    for pair, stats in synergy_data.items():
        if stats["games"] >= 50:
            win_rate = stats["wins"] / stats["games"]
            final_matrix[pair] = {
                "winrate": round(win_rate, 4),
                "sample_size": stats["games"]
            }

    # Save the synergy matrix to a JSON file
    with open(JSON_PATH, "w") as f:
        json.dump(final_matrix, f, indent=4)

    print(f"Synergy Matrix built successfully! Saved {len(final_matrix)} unique champion duos.")

if __name__ == "__main__":
    build_synergy_matrix()