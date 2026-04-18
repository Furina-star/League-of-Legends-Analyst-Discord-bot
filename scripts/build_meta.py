"""
This file builds the Meta_Champions.json file.
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

def build_meta_database() -> None:
    print(f"Loading hybrid data from {CSV_PATH} and {DB_PATH}...")

    try:
        df_csv = pd.read_csv(CSV_PATH, low_memory=False)
        if not isinstance(df_csv, pd.DataFrame):
            raise TypeError("Expected a DataFrame from read_csv, got TextFileReader instead.")
    except FileNotFoundError:
        print(f"No CSV found at {CSV_PATH}. Starting with empty DataFrame.")
        df_csv = pd.DataFrame()

    db_data = []
    if os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            try:
                cursor = conn.cursor()
                # Assuming table 'ml_training_data' exists, if not it will raise sqlite3.OperationalError
                cursor.execute("SELECT match_id, blue_win, payload FROM ml_training_data")
                for match_id, blue_win, payload_str in cursor.fetchall():
                    try:
                        payload = json.loads(payload_str)
                        payload['matchId'] = match_id
                        payload['blueWin'] = blue_win
                        db_data.append(payload)
                    except json.JSONDecodeError:
                        continue

            except sqlite3.Error as e:
                print(f"Failed to read database: {e}")

    df_db = pd.DataFrame(db_data) if db_data else pd.DataFrame()

    # Combine datasets
    if df_csv.empty and df_db.empty:
        print("❌ No data available to build meta.")
        return

    df_list = [df for df in [df_csv, df_db] if not df.empty]
    df = pd.concat(df_list, ignore_index=True)

    print(f"Dataset combined. Processing {len(df)} total matches...")

    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    # Melt the dataframe to turn columns into rows
    blue_df = df[['blueWin'] + blue_cols].melt(id_vars=['blueWin'], value_name='champ')
    red_df = df[['blueWin'] + red_cols].melt(id_vars=['blueWin'], value_name='champ')

    # Determine who won
    blue_df['win'] = blue_df['blueWin']
    red_df['win'] = 1 - red_df['blueWin']

    # Stack Blue and Red together
    all_champs = pd.concat([blue_df[['champ', 'win']], red_df[['champ', 'win']]], ignore_index=True)

    # Free up memory immediately before math calculations
    del blue_df, red_df, df

    # Group by Champion and calculate the total games and wins instantly using C-level aggregation
    stats = all_champs.groupby('champ', as_index=False)['win'].agg(games='count', wins='sum')

    # Filter out champions with less than 50 games natively
    stats = stats[stats['games'] >= 50].copy()

    # Calculate winrates natively as a new column, removing the need for slow .iterrows() loops
    stats['winrate'] = stats['wins'] / stats['games']

    # Convert the processed columns directly into a dictionary mapping
    final_meta = stats.set_index('champ')['winrate'].to_dict()
    # --- HIGH OPTIMIZATION END ---

    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w", encoding='utf-8') as f:
        json.dump(final_meta, f, indent=4)

    print(f"Meta generation complete! Saved {len(final_meta)} champions to {JSON_PATH}")

if __name__ == "__main__":
    build_meta_database()