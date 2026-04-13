"""
This file build the Synergy_Matrix.json file.
It reads the ranked_drafts.csv file, calculates the global win rates for each champion pair, and saves it as a JSON file.
 This is used in the postgame review to show how well the champion duo performed in the current meta.
"""

import pandas as pd
import numpy as np
import json
import os
from itertools import combinations

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = str(os.path.dirname(SCRIPT_DIR))
CSV_PATH = str(os.path.join(DATA_DIR, "ranked_drafts.csv"))
JSON_PATH = str(os.path.join(DATA_DIR, "Synergy_Matrix.json"))

def build_synergy_matrix():
    print(f"Reading match data from {CSV_PATH}...")
    df = pd.read_csv(filepath_or_buffer=CSV_PATH, low_memory=False)
    assert isinstance(df, pd.DataFrame)

    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    # Ensure all champion names are treated as strings
    for col in blue_cols + red_cols:
        df[col] = df[col].astype(str)

    print("Generating 1,000,000+ champion pairs using Numpy Vectorization...")

    pair_data = []

    # 10 combinations per game
    blue_win = df['blueWin']
    for c1, c2 in combinations(blue_cols, 2):
        # np.where instantly sorts the pair alphabetically across all 50k rows
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