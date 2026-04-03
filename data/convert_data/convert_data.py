import pandas as pd

print("Loading modern 2026 dataset...")
df = pd.read_csv("2026_LoL_esports_match_data_from_OraclesElixir.csv", low_memory=False)

# 1. Map Oracle's position names to the names your bot uses
pos_map = {'top': 'Top', 'jng': 'Jungle', 'mid': 'Middle', 'bot': 'ADC', 'sup': 'Support'}

# 2. Extract Picks
players = df[df['position'] != 'team'].copy()
players['position'] = players['position'].map(pos_map)
players['col_name'] = players['side'].str.lower() + players['position'] + 'Champ'
picks = players.pivot(index='gameid', columns='col_name', values='champion')

# 3. Extract Bans & Results
teams = df[df['position'] == 'team'].copy()
blue_teams = teams[teams['side'] == 'Blue'].set_index('gameid')
red_teams = teams[teams['side'] == 'Red'].set_index('gameid')

bans_and_results = pd.DataFrame(index=teams['gameid'].unique())

# Extract the 5 bans for each team
for i in range(1, 6):
    bans_and_results[f'blueBan{i}'] = blue_teams[f'ban{i}']
    bans_and_results[f'redBan{i}'] = red_teams[f'ban{i}']

# Extract who won! (1 = Red Win, 0 = Blue Win)
bans_and_results['rResult'] = red_teams['result']

# 4. Merge everything into one perfect row per game
modern_df = picks.join(bans_and_results)

# 5. Drop any weird games (like when a team is penalized and misses a ban)
modern_df = modern_df.dropna()

# Save the new CSV!
modern_df.to_csv("Modern_LoL_Data.csv", index=False)
print("Success! Created Modern_LoL_Data.csv with exactly 20 inputs and 1 result.")