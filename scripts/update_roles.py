"""
This File updates Champion_Roles.json where it designates champions to their role according to meta.
It utilizes the hybrid dataset of baseline CSV and passively mined database data.
"""

import pandas as pd
import json
import os
import sqlite3

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
CSV_PATH  = os.path.join(DATA_DIR, "training", "upgraded_drafts.csv")
DB_PATH   = os.path.join(DATA_DIR, "live", "server_state.db")
JSON_PATH = os.path.join(DATA_DIR, "static", "Champion_Roles.json")

# Load CSV
def _load_csv_data(csv_path: str) -> pd.DataFrame:
    try:
        df_csv = pd.read_csv(filepath_or_buffer=csv_path, low_memory=False)
        if not isinstance(df_csv, pd.DataFrame):
            raise TypeError("Expected a DataFrame from read_csv, got TextFileReader instead.")
        return df_csv
    except FileNotFoundError:
        print(f"No CSV found at {csv_path}. Starting with empty DataFrame.")
        return pd.DataFrame()

# Load the Database
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

# The Main Function
def generate_dynamic_roles() -> None:
    print(f"Loading hybrid data from {CSV_PATH} and {DB_PATH}...")

    df_csv = _load_csv_data(CSV_PATH)
    df_db = _load_db_data(DB_PATH)

    # Combine datasets safely
    if df_csv.empty and df_db.empty:
        print("❌ No data available to update roles.")
        return

    # Fixes IDE concat warnings by guaranteeing strict DataFrame lists
    df_list = [df for df in [df_csv, df_db] if not df.empty]
    df = pd.concat(df_list, ignore_index=True)

    print(f"Analyzed {len(df)} matches. Sorting champions into meta buckets using vectorization...")

    #  Collapse all 10 role columns into two columns: ['position', 'champion']
    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    melted = df[blue_cols + red_cols].melt(var_name='position', value_name='champion')
    del df  # Free up RAM instantly

    # Standardize specific positions into the 5 main roles
    role_mapping = {
        'blueTop': 'TOP', 'redTop': 'TOP',
        'blueJungle': 'JUNGLE', 'redJungle': 'JUNGLE',
        'blueMid': 'MIDDLE', 'redMid': 'MIDDLE',
        'blueADC': 'BOTTOM', 'redADC': 'BOTTOM',
        'blueSupport': 'UTILITY', 'redSupport': 'UTILITY'
    }
    melted['role'] = melted['position'].map(role_mapping)

    # Instantly build a matrix of Champions (rows) vs Roles (columns)
    counts = pd.crosstab(melted['champion'], melted['role'])
    del melted  # Free up RAM instantly

    # Calculate total games and drop anomalies (< 10 total games)
    counts['total'] = counts.sum(axis=1)
    valid_champs = counts[counts['total'] >= 10].copy()

    # Divide all roles by the total simultaneously to get percentages
    pct = valid_champs.drop(columns=['total']).div(valid_champs['total'], axis=0)
    del valid_champs, counts  # Free up RAM instantly

    # Load the existing JSON to preserve our static Macro categories!
    existing_db = {}
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                existing_db = json.load(f)
        except json.JSONDecodeError:
            print("Corrupted JSON found, starting fresh macro categories.")

    # Instantly extract the champions that meet the thresholds
    new_db = {
        "PURE_ADCS": pct[pct['BOTTOM'] > 0.80].index.tolist(),
        "PURE_SUPPORTS": pct[pct['UTILITY'] > 0.80].index.tolist(),
        "FLEX_BOTS": pct[(pct['BOTTOM'] > 0.10) & (pct['BOTTOM'] <= 0.80)].index.tolist(),
        "FLEX_SUPPORTS": pct[(pct['UTILITY'] > 0.10) & (pct['UTILITY'] <= 0.80)].index.tolist(),
        "KNOWN_MIDS": pct[pct['MIDDLE'] > 0.15].index.tolist(),
        "KNOWN_TOPS": pct[pct['TOP'] > 0.15].index.tolist(),
        "KNOWN_JUNGLES": pct[pct['JUNGLE'] > 0.15].index.tolist(),

        "DAMAGE_AD": existing_db.get("DAMAGE_AD", []),
        "DAMAGE_AP": existing_db.get("DAMAGE_AP", []),
        "FRONTLINE": existing_db.get("FRONTLINE", []),
        "RANGED": existing_db.get("RANGED", []),
        "HARD_CC": existing_db.get("HARD_CC", []),
        "ENGAGE": existing_db.get("ENGAGE", []),
        "WAVECLEAR": existing_db.get("WAVECLEAR", []),
        "SCALING": existing_db.get("SCALING", [])
    }

    # Safely create directories if they don't exist yet
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)

    # Save over the old JSON file
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(new_db, f, indent=4)

    print("Successfully created a highly optimized, data-driven roles database!")

if __name__ == "__main__":
    generate_dynamic_roles()