import pandas as pd

"""
STEP 1: THE MINER (Add 5k new games)
    - Open `data_miner.py`.
    - Increase TARGET_MATCHES by 5,000 (e.g., 50000 -> 55000).
    - Run `data_miner.py` and let it finish.

STEP 2: THE PRUNER (Delete 5k old games)
    - Run this script (`update_patch.py`).
    - This chops off the oldest 5,000 games, resetting the CSV to a perfect 50k.

STEP 3: THE MATH (Recalculate the Meta)
    - Run `build_synergy_matrix.py`.
    - This updates the JSON file with the newest champion synergies.

STEP 4: THE BRAIN SURGERY (Retrain the AI)
    - Run `train_model.py`.
    - The AI will study the new CSV and new JSON to build a new .pth file.

STEP 5: DEPLOYMENT
    - Restart your Discord Bot script.
"""

print("Loading 55,000 matches...")
df = pd.read_csv("data/ranked_drafts.csv")

# Keep only the 50,000 MOST RECENT games (drops the oldest ones at the top)
df = df.tail(50000)

df.to_csv("data/ranked_drafts.csv", index=False)
print("✅ Successfully pruned the oldest 5,000 matches. CSV is back to 50k!")