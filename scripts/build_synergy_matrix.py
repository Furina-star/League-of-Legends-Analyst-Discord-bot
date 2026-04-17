"""
This file build the Synergy_Matrix.json file.
It reads the upgraded_drafts.csv file AND the passively mined SQLite database,
calculates the global win rates for each champion pair, and saves it as a JSON file.
"""

import pandas as pd
import numpy as np
import json
import os
import sqlite3
from itertools import combinations

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
CSV_PATH  = os.path.join(DATA_DIR, "training", "upgraded_drafts.csv")
DB_PATH   = os.path.join(DATA_DIR, "live", "server_state.db")
JSON_PATH = os.path.join(DATA_DIR, "static", "Meta_Champions.json")

def build_synergy_matrix():
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
                pass # Table might not exist yet

    if db_data:
        df_db = pd.DataFrame(db_data)
        df = pd.concat([df_csv, df_db], ignore_index=True)
    else:
        df = df_csv

    assert isinstance(df, pd.DataFrame)

    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    # Ensure all champion names are treated as strings
    for col in blue_cols + red_cols:
        df[col] = df[col].astype(str)

    print(f"Generating champion pairs using Numpy Vectorization across {len(df)} matches...")

    pair_data = []

    # 10 combinations per game
    blue_win = df['blueWin']
    for c1, c2 in combinations(blue_cols, 2):
        # np.where instantly sorts the pair alphabetically
        pairs = np.where(df[c1] < df[c2], df[c1] + "-" + df[c2], df[c2] + "-" + df[c1])
        temp_df = pd.DataFrame({'pair': pairs, 'win': blue_win})
        pair_data.append(temp_df)

    # If blueWin is 1, red_win is 0, and vice versa
    red_win = 1 - df['blueWin']
    for c1, c2 in combinations(red_cols, 2):
        pairs = np.where(df[c1] < df[c2], df[c1] + "-" + df[c2], df[c2] + "-" + df[c1])
        temp_df = pd.DataFrame({'pair': pairs, 'win': red_win})
        pair_data.append(temp_df)

    # All data into one massive table
    print("Calculating global synergy win rates...")
    all_pairs = pd.concat(pair_data, ignore_index=True)

    # Instantly using Pandas GroupBy
    stats = all_pairs.groupby('pair').agg(
        wins=('win', 'sum'),
        games=('win', 'count')
    )

    # Filter noise (games >= 50) and calculate final math
    valid_stats = stats[stats['games'] >= 50].copy()
    valid_stats['winrate'] = (valid_stats['wins'] / valid_stats['games']).round(4)

    # Clean up the dataframe columns to match your exact JSON structure
    valid_stats = valid_stats[['winrate', 'games']].rename(columns={'games': 'sample_size'})

    # Convert directly to JSON without a single for-loop
    final_matrix = valid_stats.to_dict(orient='index')

    with open(JSON_PATH, "w") as f:
        json.dump(final_matrix, f, indent=4)

    print(f"Synergy Matrix built successfully! Saved {len(final_matrix)} unique champion duos.")

if __name__ == "__main__":
    build_synergy_matrix()