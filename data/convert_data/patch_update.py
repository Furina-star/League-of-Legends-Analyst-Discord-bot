"""
This script automates the entire "Rolling Window" update process.

BEFORE RUNNING:
1. Open `data_miner.py` and increase `TARGET_MATCHES` by 5,000 (e.g., 50000 -> 55000).
2. Save `data_miner.py`.
3. Run this script! It will handle the rest.
"""

import pandas as pd
import subprocess
import sys
import os

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = str(os.path.dirname(SCRIPT_DIR))

def run_script(script_name):
    script_path = str(os.path.join(SCRIPT_DIR, script_name))
    print(f"\n🚀 Starting: {script_path}...")
    try:
        subprocess.run([sys.executable, script_path], check=True)
        print(f"Finished: {script_path}!")
    except subprocess.CalledProcessError:
        print(f"\nError occurred while running {script_path}.")
        sys.exit(1)


def prune_database():
    csv_path = str(os.path.join(DATA_DIR, "ranked_drafts.csv"))
    print(f"\n Loading matches from {csv_path}...")

    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}!")
        sys.exit(1)

    df = pd.read_csv(filepath_or_buffer=csv_path, low_memory=False)
    assert isinstance(df, pd.DataFrame)

    original_count = len(df)
    df = df.tail(50000)
    df.to_csv(csv_path, index=False)
    print(f"✅ Successfully pruned {original_count - len(df)} old matches. CSV is back to 50k!")


if __name__ == "__main__":
    confirm = input("Did you increase TARGET_MATCHES by 5,000 in data_miner.py? (y/n): ")
    if confirm.lower() != 'y':
        print("🛑 Stopping. Please go update data_miner.py first!")
        sys.exit()

    run_script("data_miner.py")
    prune_database()
    run_script("build_synergy_matrix.py")
    run_script("build_meta.py")
    run_script("build_items.py")
    run_script("build_runes.py")

    # Dynamic path for train_model.py in the root directory
    main_dir = os.path.dirname(DATA_DIR)
    train_script = os.path.join(main_dir, "train_model.py")
    print(f"\n🚀 Starting: {train_script}...")
    try:
        subprocess.run([sys.executable, train_script], check=True)
    except subprocess.CalledProcessError:
        sys.exit(1)

    print("Pipeline Complete!")