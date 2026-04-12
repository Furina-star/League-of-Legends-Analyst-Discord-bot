import pandas as pd
import json
import os

# Get the directory this exact script is sitting in (.../data/convert_data/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Move up one level to the parent directory (.../data/)
DATA_DIR = os.path.dirname(SCRIPT_DIR)

# Construct the absolute paths to your files
DEFAULT_CSV = os.path.join(DATA_DIR, "ranked_drafts.csv")
DEFAULT_JSON = os.path.join(DATA_DIR, "Champion_Roles.json")


def generate_dynamic_roles(csv_path=DEFAULT_CSV, output_path=DEFAULT_JSON):
    print(f"Reading match data from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Map the exact column names from your CSV
    roles_map = {
        "TOP": ['blueTop', 'redTop'],
        "JUNGLE": ['blueJungle', 'redJungle'],
        "MIDDLE": ['blueMid', 'redMid'],
        "BOTTOM": ['blueADC', 'redADC'],
        "UTILITY": ['blueSupport', 'redSupport']
    }

    # Dictionary to track counts: { "Yasuo": {"TOP": 50, "MIDDLE": 200...} }
    champ_counts = {}

    for role_name, columns in roles_map.items():
        # Combine blue and red columns for this role
        all_champs_in_role = pd.concat([df[columns[0]], df[columns[1]]])
        counts = all_champs_in_role.value_counts()

        for champ, count in counts.items():
            if champ not in champ_counts:
                champ_counts[champ] = {"TOP": 0, "JUNGLE": 0, "MIDDLE": 0, "BOTTOM": 0, "UTILITY": 0}
            champ_counts[champ][role_name] += count

    print(f"Analyzed {len(df)} matches. Sorting champions into meta buckets...")

    # Set up the new DB structure
    new_db = {
        "PURE_ADCS": [], "PURE_SUPPORTS": [],
        "FLEX_BOTS": [], "FLEX_SUPPORTS": [],
        "KNOWN_MIDS": [], "KNOWN_TOPS": [], "KNOWN_JUNGLES": []
    }

    # Sort logic based on actual mathematical play-rates
    for champ, roles in champ_counts.items():
        total_games = sum(roles.values())

        # Skip weird 1-trick anomalies (e.g. someone playing Yuumi Jungle once)
        if total_games < 10:
            continue

        # Calculate percentages
        top_pct = roles["TOP"] / total_games
        jg_pct = roles["JUNGLE"] / total_games
        mid_pct = roles["MIDDLE"] / total_games
        adc_pct = roles["BOTTOM"] / total_games
        sup_pct = roles["UTILITY"] / total_games

        # Bot Lane Sorting
        if adc_pct > 0.80:
            new_db["PURE_ADCS"].append(champ)
        elif adc_pct > 0.10:  # If played ADC more than 10% of the time
            new_db["FLEX_BOTS"].append(champ)

        # Support Sorting
        if sup_pct > 0.80:
            new_db["PURE_SUPPORTS"].append(champ)
        elif sup_pct > 0.10:
            new_db["FLEX_SUPPORTS"].append(champ)

        #  Solo Lanes & Jungle Sorting
        if mid_pct > 0.15:
            new_db["KNOWN_MIDS"].append(champ)
        if top_pct > 0.15:
            new_db["KNOWN_TOPS"].append(champ)
        if jg_pct > 0.15:
            new_db["KNOWN_JUNGLES"].append(champ)

    # Save over the old JSON file
    with open(output_path, "w") as f:
        json.dump(new_db, f, indent=4)

    print("Successfully created a data-driven database based on your current patch!")

if __name__ == "__main__":
    generate_dynamic_roles()