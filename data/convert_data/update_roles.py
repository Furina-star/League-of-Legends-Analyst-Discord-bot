"""
This File, updates Champion_Roles.json where it designates champions to their role according to meta.
"""

import pandas as pd
import json
import os

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = str(os.path.dirname(SCRIPT_DIR))
DEFAULT_CSV = str(os.path.join(DATA_DIR, "ranked_drafts.csv"))
DEFAULT_JSON = str(os.path.join(DATA_DIR, "Champion_Roles.json"))

def generate_dynamic_roles(csv_path=DEFAULT_CSV, output_path=DEFAULT_JSON):
    print(f"Reading match data from {csv_path}...")

    # Use low_memory=False to prevent chunking warnings
    df = pd.read_csv(filepath_or_buffer=csv_path, low_memory=False)
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
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
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
    with open(output_path, "w") as f:
        json.dump(new_db, f, indent=4)

    print("Successfully created a highly optimized, data-driven database!")

if __name__ == "__main__":
    generate_dynamic_roles()