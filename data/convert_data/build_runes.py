"""
This is a script that get all the Keystone Runes.
"""

import urllib.request
import json
import os

# Explicit path casting
SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
FILE_PATH = str(os.path.join(SCRIPT_DIR, '..', 'Keystone_Runes.json'))

def update_rune_dictionary():
    print("Fetching the latest League of Legends patch version...")
    version_url = "https://ddragon.leagueoflegends.com/api/versions.json"

    with urllib.request.urlopen(version_url) as response:
        versions = json.loads(response.read().decode())
        latest_patch = versions[0]

    print(f"Latest patch is {latest_patch}. Downloading Rune data...")
    rune_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_patch}/data/en_US/runesReforged.json"

    with urllib.request.urlopen(rune_url) as response:
        rune_data = json.loads(response.read().decode())

    # Flatten the deeply nested Riot JSON structure in a single pass
    clean_dict = {
        str(rune['id']): rune['name']
        for tree in rune_data
        for slot in tree['slots']
        for rune in slot['runes']
    }

    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(clean_dict, f, indent=4)

    print(f"Successfully mapped {len(clean_dict)} runes and saved to {FILE_PATH}!")

if __name__ == "__main__":
    update_rune_dictionary()