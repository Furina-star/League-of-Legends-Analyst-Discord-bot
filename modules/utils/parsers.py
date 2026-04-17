"""
This is the parsers module, which contains all the helper functions for parsing and processing data related to League of Legends.
This includes functions for parsing Riot IDs, extracting win rates from rank strings, sorting team compositions by role, and detecting autofill situations by comparing a player's primary role from match history against their current inferred position.
These functions are designed to be reusable across different parts of the bot, ensuring consistent data handling and improving code maintainability.
"""

import re
import logging
from config import QUEUE_MAP
from typing import Optional

# Get the logging system
logger = logging.getLogger(__name__)

# This class handles all stats calculation and such
class ParsedStats:
    def __init__(self, stats: dict):
        # Base Stats
        self.champ = stats.get('championName', '')
        self.kills = stats.get('kills', 0)
        self.deaths = stats.get('deaths', 0)
        self.assists = stats.get('assists', 0)
        self.damage = stats.get('totalDamageDealtToChampions', 0)
        self.damage_taken = stats.get('totalDamageTaken', 0)
        self.vision_wards = stats.get('visionWardsBoughtInGame', 0)
        self.role = stats.get('teamPosition', '')
        self.win = stats.get('win', False)
        self.time = stats.get('gameDuration', 0)
        self.game_mode = stats.get('gameMode', 'Unknown Mode')
        self.match_id = stats.get('matchId', 'Unknown ID')
        self.cs = stats.get('totalMinionsKilled', 0) + stats.get('neutralMinionsKilled', 0)
        self.gold = stats.get('goldEarned', 0)
        self.vision_score = stats.get('visionScore', 0)
        self.healing = stats.get('totalHeal', 0)

        # Summoner Spells
        self.spell1_id = stats.get('summoner1Id', 0)
        self.spell2_id = stats.get('summoner2Id', 0)

        # Challenge Stats (For Extra Tags and Roasts!)
        self.challenges = stats.get('challenges', {})
        self.skillshots_dodged = self.challenges.get('skillshotsDodged', 0)
        self.solo_kills = self.challenges.get('soloKills', 0)
        self.dodge_streak = self.challenges.get('maxDodgeSteak', 0)  # Yes, Riot typos it as 'steak'
        self.kda = self.challenges.get('kda', 0.0)
        self.team_damage_pct = self.challenges.get('teamDamagePercentage', 0.0)
        self.dpm = self.challenges.get('damagePerMinute', 0.0)
        self.cs_advantage = self.challenges.get('maxCsAdvantageOnLaneOpponent', 0)
        self.plates = self.challenges.get('turretPlatesTaken', 0)
        self.lucky_survivals = self.challenges.get('survivedSingleDigitHpCount', 0)
        self.outnumbered_kills = self.challenges.get('outnumberedKills', 0)

        # Advanced Calculated Stats (For Tags and Roasts!)
        self.minutes = self.time / 60.0 if self.time > 0 else 1.0
        self.cs_per_min = self.cs / self.minutes

        self.team_kills = stats.get('teamKills', 1)
        self.kp_percent = ((self.kills + self.assists) / self.team_kills) * 100 if self.team_kills > 0 else 0.0

        # Objective & Milestone Stats
        self.first_blood = stats.get('firstBloodKill', False)
        self.pentas = stats.get('pentaKills', 0)
        self.quadras = stats.get('quadraKills', 0)
        self.turrets = stats.get('turretKills', 0)
        self.stolen_objs = stats.get('objectivesStolen', 0)
        self.dragons = stats.get('dragonKills', 0)

        # Get the Rival's stats
        rival_data = stats.get('rivalStats') or {}
        self.rival = rival_data if rival_data else None
        if self.rival:
            self.r_dmg = self.rival.get('totalDamageDealtToChampions', 0)
            self.r_gold = self.rival.get('goldEarned', 0)
            self.r_cs = self.rival.get('totalMinionsKilled', 0) + self.rival.get('neutralMinionsKilled', 0)
            self.r_champ = self.rival.get('championName', 'your lane opponent')
            self.r_vision = self.rival.get('visionScore', 0)
            self.r_deaths = self.rival.get('deaths', 0)
        else:
            self.r_dmg = self.r_gold = self.r_cs = self.r_vision = self.r_deaths = 0
            self.r_champ = "Unknown"

        # Item Extraction
        self.items = [
            stats.get('item0', 0), stats.get('item1', 0), stats.get('item2', 0),
            stats.get('item3', 0), stats.get('item4', 0), stats.get('item5', 0)
        ]
        self.item_count = sum(1 for i in self.items if i != 0)
        self.trinket = stats.get('item6', 0)

        # Keystone Extraction
        self.keystone_id = None
        try:
            self.keystone_id = str(stats['perks']['styles'][0]['selections'][0]['perk'])
            self.primary_style = stats['perks']['styles'][0]['style']  # Tracks Precision, Domination, etc.
        except (KeyError, IndexError):
            self.keystone_id = None
            self.primary_style = None

    # Calculates a rough performance letter grade.
    def get_grade(self) -> str:
        kda = (self.kills + self.assists) / max(1, self.deaths)

        # KDA & KP Summations
        score = sum(kda >= t for t in (2.0, 3.5, 5.0)) - (2 * (kda < 1.0))
        score += sum(self.kp_percent >= t for t in (40.0, 60.0))

        # Role-Specific Objectives
        if self.role == "UTILITY":
            score += sum(self.vision_score >= self.minutes * t for t in (1.0, 1.5, 2.2))
        else:
            limits = (4.0, 5.0, 6.5) if self.role == "JUNGLE" else (5.0, 6.5, 8.0)
            score += sum(self.cs_per_min >= t for t in limits)

        # Penalties & Combat Bonus
        score += (self.deaths == 0) - (self.deaths >= 7) - (self.deaths >= 10)

        dpm_calc = self.dpm if self.dpm > 0 else (self.damage / max(1.0, self.minutes))
        score += (dpm_calc >= 800.0 or self.healing >= 15000)

        # O(1) Array Lookup for Final Grade
        grades = ["D", "D", "D", "C", "B", "A", "S-", "S", "S+"]
        return grades[max(0, min(8, int(score)))]

# Find duos
def find_duos(player_histories: list) -> set:
    duos = set()
    # Compare every player's match history against every other player's history
    for i in range(len(player_histories)):
        for j in range(i + 1, len(player_histories)):
            p1_id, p1_matches = player_histories[i]
            p2_id, p2_matches = player_histories[j]

            # If the lists intersect (share a Match ID), they're playing together lol
            if p1_matches and p2_matches:
                shared_games = set(p1_matches).intersection(p2_matches)

                if len(shared_games) >= 2:  # If they have 2 or more shared games in their recent history, they're probably duos
                    duos.add(p1_id)
                    duos.add(p2_id)
    return duos

# this is to prevent the user from formatting it wrong, for example they might type "Hide on bush KR1" instead of "Hide on bush#KR1".
def parse_riot_id(full_riot_id: str):
    full_riot_id = full_riot_id.strip()
    if len(full_riot_id) > 22:  # 16 (name) + 1 (#) + 5 (tag)
        return None, None

    if '#' in full_riot_id:
        game_name, tag_line = full_riot_id.split('#', 1)
    else:
        parts = full_riot_id.rsplit(' ', 1)
        if len(parts) == 2:
            game_name, tag_line = parts[0], parts[1]
        else:
            return None, None  # Returns None if they formatted it completely wrong

    return game_name.strip(), tag_line.strip()

# Initiate Winrate as a function
def parse_winrate(rank_string):
    if not rank_string or "Unranked" in rank_string:
        return 50.0  # If unranked or missing, assume an average 50% player

    # Searches for numbers directly followed by "% WR"
    match = re.search(r"([\d.]+)%\sWR", rank_string)
    if match:
        return float(match.group(1))
    return 50.0

# Initiate Role Sorter as a function.
def _assign_role_from_pool(roles, unassigned, role_idx, db_key, meta_db):
    if roles[role_idx] is not None:
        return
    pool = meta_db.get(db_key, set())
    for i, champ in enumerate(unassigned):
        if champ in pool:
            roles[role_idx] = champ
            unassigned.pop(i)
            return

# Sort Team Composition by role, not by pick
def sort_team_roles(team_participants, champ_dict, meta_db):
    roles = [None] * 5
    unassigned = []

    for player in team_participants:
        champ_name = champ_dict.get(str(player['championId']), "Unknown")
        if roles[1] is None and 11 in (player.get('spell1Id'), player.get('spell2Id')):
            roles[1] = champ_name
        else:
            unassigned.append(champ_name)

    # Use the new external helper instead of a nested function
    _assign_role_from_pool(roles, unassigned, 3, "PURE_ADCS", meta_db)
    _assign_role_from_pool(roles, unassigned, 4, "PURE_SUPPORTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 3, "FLEX_BOTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 4, "FLEX_SUPPORTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 2, "KNOWN_MIDS", meta_db)
    _assign_role_from_pool(roles, unassigned, 0, "KNOWN_TOPS", meta_db)

    for i in range(5):
        if roles[i] is None and unassigned:
            roles[i] = unassigned.pop(0)

    if None in roles or unassigned:
        return [champ_dict.get(str(p['championId']), "Unknown") for p in team_participants]

    return roles

# Detect's if the enemy is Autofilled
def detect_autofill(primary_role: str, current_position: str) -> bool:
    if not primary_role or not current_position:
        return False

    return primary_role != current_position

# Initiate the ban logic as a function
def extract_bans(match_data: dict, champ_dict: dict):
    blue_bans, red_bans = ["None"] * 5, ["None"] * 5
    b_count, r_count = 0, 0
    for ban in match_data.get('bannedChampions', []):
        c_name = champ_dict.get(str(ban['championId']), "None")
        if ban['teamId'] == 100 and b_count < 5:
            blue_bans[b_count] = c_name
            b_count += 1
        elif ban['teamId'] == 200 and r_count < 5:
            red_bans[r_count] = c_name
            r_count += 1
    return blue_bans, red_bans

# Initiate the checking logic as a function
def check_if_bot(champ_name: str, raw_team: list, champ_dict: dict):
    for p in raw_team:
        if champ_dict.get(str(p['championId']), "Unknown") == champ_name:
            return p.get('bot', False) or not p.get('puuid')
    return False

# Formats the team display strings.
def format_team_display(team_picks: list, raw_team: list, meta_db: dict, champ_dict: dict):
    display = []
    for c in team_picks:
        meta_wr = meta_db.get(c, 0.5000) * 100
        # Pass the champ_dict into the bot checker!
        bot_tag = "🤖 " if check_if_bot(c, raw_team, champ_dict) else ""
        display.append(f"{bot_tag}{c} `[{meta_wr:.1f}%]`")
    return display

# Isolates a single player's stats from a match and calculates team totals
def extract_postgame_stats(match_data: dict, puuid: str, match_id: str) -> Optional[dict]:
    if not isinstance(match_data, dict):
        return None

    info = match_data.get('info', {})
    participants = info.get('participants', [])

    # Find the target player using next()
    player = next((p for p in participants if p.get('puuid') == puuid), None)
    if not player:
        return None

    # Inject match-level data
    player['gameDuration'] = info.get('gameDuration', 0)
    player['gameMode'] = QUEUE_MAP.get(info.get('queueId', 0), info.get('gameMode', 'UNKNOWN'))
    player['matchId'] = match_id

    # Setup variables for rival and team calculations
    team_id = player.get('teamId')
    role = player.get('teamPosition', '')
    enemy_team_id = 200 if team_id == 100 else 100

    # Calculate total team kills using a list comprehension
    team_kills = sum(p.get('kills', 0) for p in participants if p.get('teamId') == team_id)
    player['teamKills'] = max(team_kills, 1)  # Prevent division by zero

    # Find the Lane Rival
    if role and role != "Invalid":
        player['rivalStats'] = next(
            (p for p in participants if p.get('teamId') == enemy_team_id and p.get('teamPosition') == role),
            None
        )
    else:
        player['rivalStats'] = None

    return player

# Instantly resolves abbreviations or partial names to full champion names
def quick_resolve_champion(raw_name: str, champ_db: dict) -> str:
    raw = re.sub(r'[^a-zA-Z0-9]', '', raw_name).lower()

    # Common speed aliases
    aliases = {
        "j4": "JarvanIV", "mf": "MissFortune", "tf": "TwistedFate",
        "gp": "Gangplank", "nunu": "Nunu", "renata": "Renata",
        "asol": "AurelionSol", "yi": "MasterYi", "tk": "TahmKench",
        "wukong": "MonkeyKing", "lb": "Leblanc", "bardo": "Bard",
        "ww": "Warwick", "nid": "Nidalee", "cass": "Cassiopeia",
        "ez": "Ezreal", "cait": "Caitlyn", "tris": "Tristana",
        "kata": "Katarina", "cho": "Chogath", "rek": "RekSai",
        "kog": "KogMaw", "naut": "Nautilus", "sej": "Sejuani",
        "ksante": "KSante", "bel": "Belveth"
    }
    if raw in aliases:
        return aliases[raw]

    # Partial match (e.g., "yas" -> "Yasuo", "lee" -> "Lee Sin")
    for full_name in champ_db.values():
        if full_name.lower().startswith(raw):
            return full_name

    # Fallback if no match is found
    return raw_name.title().replace(" ", "").replace("'", "")

# Extracts and formats live spectator V5 Riot IDs based on sorted draft positions
def extract_live_player_names(sorted_picks: list, raw_team: list, champ_dict: dict) -> list:
    names = []
    for pick in sorted_picks:
        # Securely resolve the player, translating Riot's internal 'MonkeyKing' to 'Wukong'
        player = next((p for p in raw_team if champ_dict.get(str(p['championId']), 'Unknown').replace('MonkeyKing', 'Wukong') == pick), None)

        if player:
            # V5 API uses 'riotId' combined string (e.g., Faker#KR1). Slice off the tag
            riot_id = player.get('riotId', '')
            if '#' in riot_id:
                names.append(riot_id.split('#')[0])
            else:
                # Fallbacks for older data or custom game endpoints
                names.append(player.get('riotIdGameName') or player.get('summonerName') or "Unknown")
        else:
            names.append("Unknown")
    return names