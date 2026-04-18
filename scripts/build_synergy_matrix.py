"""
This file builds the Synergy_Matrix.json file.
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
JSON_PATH = os.path.join(DATA_DIR, "static", "Synergy_Matrix.json")

# load the CSV
def _load_csv_data(csv_path: str) -> pd.DataFrame:
    try:
        df_csv = pd.read_csv(filepath_or_buffer=csv_path, low_memory=False)
        if not isinstance(df_csv, pd.DataFrame):
            raise TypeError("Expected a DataFrame from read_csv, got TextFileReader instead.")
        return df_csv
    except FileNotFoundError:
        print(f"No CSV found at {csv_path}. Starting with empty DataFrame.")
        return pd.DataFrame()

# Load the database
def _load_db_data(db_path: str) -> pd.DataFrame:
    if not os.path.exists(db_path):
        return pd.DataFrame()

    db_data = []
    with sqlite3.connect(db_path) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT match_id, blue_win, payload FROM ml_training_data")
            for match_id, blue_win, payload_str in cursor.fetchall():
                try:
                    payload = json.loads(payload_str)
                    payload['blueWin'] = blue_win
                    db_data.append(payload)
                except json.JSONDecodeError:
                    continue
        except sqlite3.Error as e:
            print(f"Failed to read database: {e}")

    return pd.DataFrame(db_data) if db_data else pd.DataFrame()

# Pair Generation
def _generate_pairs(df: pd.DataFrame) -> list:
    pair_data = []
    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    # Ensure all champion names are treated as strings
    for col in blue_cols + red_cols:
        df[col] = df[col].astype(str)

    # Combinations for Blue
    blue_win = df['blueWin'].copy()
    for c1, c2 in combinations(blue_cols, 2):
        pairs = np.where(df[c1] < df[c2], df[c1] + "-" + df[c2], df[c2] + "-" + df[c1])
        pair_data.append(pd.DataFrame({'pair': pairs, 'win': blue_win}))

    # Combinations for Red
    red_win = 1 - df['blueWin']
    for c1, c2 in combinations(red_cols, 2):
        pairs = np.where(df[c1] < df[c2], df[c1] + "-" + df[c2], df[c2] + "-" + df[c1])
        pair_data.append(pd.DataFrame({'pair': pairs, 'win': red_win}))

    return pair_data

# The main function that orchestrates the entire synergy matrix building process
def build_synergy_matrix() -> None:
    print(f"Loading hybrid data from {CSV_PATH} and {DB_PATH}...")

    df_csv = _load_csv_data(CSV_PATH)
    df_db = _load_db_data(DB_PATH)

    # Combine datasets safely
    if df_csv.empty and df_db.empty:
        print("❌ No data available to build synergy matrix.")
        return

    df_list = [df for df in [df_csv, df_db] if not df.empty]
    df = pd.concat(df_list, ignore_index=True)

    print(f"Generating champion pairs using Numpy Vectorization across {len(df)} matches...")

    pair_data = _generate_pairs(df)

    # Free up memory before the massive concatenation
    del df, df_csv, df_db

    print("Calculating global synergy win rates...")
    all_pairs = pd.concat(pair_data, ignore_index=True)

    del pair_data # Free memory again

    # Instantly using Pandas GroupBy
    stats = all_pairs.groupby('pair', as_index=False).agg(
        wins=('win', 'sum'),
        games=('win', 'count')
    )

    del all_pairs # Clear final massive dataframe

    # Filter noise (games >= 50) and calculate final math
    valid_stats = stats[stats['games'] >= 50].copy()
    valid_stats['winrate'] = (valid_stats['wins'] / valid_stats['games']).round(4)

    # Clean up the dataframe columns to match your exact JSON structure
    valid_stats = valid_stats[['pair', 'winrate', 'games']].rename(columns={'games': 'sample_size'})
    valid_stats.set_index('pair', inplace=True)

    # Convert directly to JSON without a single for-loop
    final_matrix = valid_stats.to_dict(orient='index')

    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w", encoding='utf-8') as f:
        json.dump(final_matrix, f, indent=4)

    print(f"Synergy Matrix built successfully! Saved {len(final_matrix)} unique champion duos.")

if __name__ == "__main__":
    build_synergy_matrix()