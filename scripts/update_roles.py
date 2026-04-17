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
JSON_PATH = os.path.join(DATA_DIR, "static", "Meta_Champions.json")

def generate_dynamic_roles():
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

    print(f"Analyzed {len(df)} matches. Sorting champions into meta buckets using vectorization...")

    #  Collapse all 10 role columns into two columns: ['position', 'champion']
    blue_cols = ['blueTop', 'blueJungle', 'blueMid', 'blueADC', 'blueSupport']
    red_cols = ['redTop', 'redJungle', 'redMid', 'redADC', 'redSupport']

    melted = df[blue_cols + red_cols].melt(var_name='position', value_name='champion')

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

    # Calculate total games and drop anomalies (< 10 total games)
    counts['total'] = counts.sum(axis=1)
    valid_champs = counts[counts['total'] >= 10].copy()

    # Divide all roles by the total simultaneously to get percentages
    pct = valid_champs.drop(columns=['total']).div(valid_champs['total'], axis=0)

    # Load the existing JSON to preserve our static Macro categories!
    existing_db = {}
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r") as f:
            existing_db = json.load(f)

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

    # Save over the old JSON file
    with open(JSON_PATH, "w") as f:
        json.dump(new_db, f, indent=4)

    print("Successfully created a highly optimized, data-driven roles database!")

if __name__ == "__main__":
    generate_dynamic_roles()