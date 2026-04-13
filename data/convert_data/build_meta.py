"""
This file build the Meta_Champions.json file.
It reads the ranked_drafts.csv file, calculates the global win rates for each champion, and saves it as a JSON file.
This is used in the postgame review to show how well the champion performed in the current meta.
"""

import pandas as pd
import json
import os

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = str(os.path.dirname(SCRIPT_DIR))
CSV_PATH = os.path.join(DATA_DIR, "ranked_drafts.csv")
JSON_PATH = os.path.join(DATA_DIR, "Meta_Champions.json")

def build_meta_database():
    print(f"Reading match data from {CSV_PATH}...")

    df: pd.DataFrame = pd.read_csv(CSV_PATH)

    print(f"Calculating Global Win Rates across {len(df)} matches using Pandas Vectorization...")

    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    # Melt the dataframe to turn columns into rows superfast.
    blue_df = df[['blueWin'] + blue_cols].melt(id_vars=['blueWin'], value_name='champ')
    red_df = df[['blueWin'] + red_cols].melt(id_vars=['blueWin'], value_name='champ')

    # Determine who won (Blue wins if 1, Red wins if 0)
    blue_df['win'] = blue_df['blueWin']
    red_df['win'] = 1 - red_df['blueWin']

    # Stack Blue and Red together into one massive list of champions
    all_champs = pd.concat([blue_df[['champ', 'win']], red_df[['champ', 'win']]])

    # Group by Champion and calculate the total games and wins instantly
    stats = all_champs.groupby('champ')['win'].agg(games='count', wins='sum')

    # Calculate the final percentages
    final_meta = {}
    for champ, row in stats.iterrows():
        champ_str = str(champ)  # Ensure it's a string for the JSON key

        # Only log them if they've been played at least 50 times
        if row['games'] >= 50:
            win_rate = row['wins'] / row['games']
            final_meta[champ_str] = round(win_rate, 4)
        else:
            final_meta[champ_str] = 0.5000

    # Save the brain
    with open(JSON_PATH, "w") as f:
        json.dump(final_meta, f, indent=4)

    print(f"Meta Database built successfully! Tracked {len(final_meta)} champions.")


if __name__ == "__main__":
    build_meta_database()