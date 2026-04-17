"""
This file build the Meta_Champions.json file.
It reads the upgraded_drafts.csv file AND the passively mined SQLite database,
calculates the global win rates for each champion, and saves it as a JSON file.
"""

import pandas as pd
import json
import os
import sqlite3

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
CSV_PATH  = os.path.join(DATA_DIR, "training", "upgraded_drafts.csv")
DB_PATH   = os.path.join(DATA_DIR, "live", "server_state.db")
JSON_PATH = os.path.join(DATA_DIR, "static", "Meta_Champions.json")

def build_meta_database():
    print(f"Loading hybrid data from {CSV_PATH} and {DB_PATH}...")
    df_csv = pd.read_csv(CSV_PATH, low_memory=False)

    db_data = []
    if os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT match_id, blue_win, payload FROM ml_training_data")
                for match_id, blue_win, payload_str in cursor.fetchall():
                    payload = json.loads(payload_str)
                    payload['blueWin'] = blue_win
                    db_data.append(payload)
            except Exception:
                pass # Table might not exist yet if bot hasn't mined anything

    if db_data:
        df_db = pd.DataFrame(db_data)
        df = pd.concat([df_csv, df_db], ignore_index=True)
    else:
        df = df_csv

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