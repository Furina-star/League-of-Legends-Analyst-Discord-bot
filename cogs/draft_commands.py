"""
This part of the Discord  League Analyst Bot
is all about the draft commands,
commands that analyze the live game, predict the win condition, and scout the enemy team.
"""
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
import logging
from utils.embed_formatter import build_predict_embeds, build_scout_embed
from utils.views import PredictView
from discord.utils import escape_mentions

# Get the logging system
logger = logging.getLogger(__name__)

# Initiate Riot ID Parser as a function.
# this is to prevent the user from formatting it wrong, for example they might type "Hide on bush KR1" instead of "Hide on bush#KR1".
def parse_riot_id(full_riot_id: str):
    if len(full_riot_id) > 22:  # 16 (name) + 1 (#) + 5 (tag)
        return None, None
    
    if '#' in full_riot_id:
        game_name, tag_line = full_riot_id.split('#', 1)
    else:
        parts = full_riot_id.rsplit(' ', 1)
        if len(parts) == 2:
            game_name, tag_line = parts[0], parts[1]
        else:
            return None, None # Returns None if they formatted it completely wrong

    return game_name.strip(), tag_line.strip()

# Initiate Winrate as a function
def parse_winrate(rank_string):
    if not rank_string or "Unranked" in rank_string:
        return 50.0 # If unranked or missing, assume an average 50% player

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

# Cog Class
class DraftCommands(commands.Cog):
    def __init__(self, bot, riot_client, ai_system, meta_db, champ_dict, role_db):
        # Store everything here to use for the bot commands yeah yessir.
        self.bot = bot
        self.riot = riot_client
        self.ai = ai_system
        self.meta_db = meta_db
        self.champ_dict = champ_dict
        self.server_dict = bot.server_dict
        self.role_db = role_db

    # Autocomplete logic for Scout and Predict
    async def server_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:

        # Get the keys from server dictionary
        servers = list(self.server_dict.keys())

        choices = [
            app_commands.Choice(name=server.upper(), value=server.upper())
            for server in servers if current.lower() in server.lower()
        ]

        return choices[:25]

    # Initiate the ban logic as a function
    def _extract_bans(self, match_data):
        blue_bans, red_bans = ["None"] * 5, ["None"] * 5
        b_count, r_count = 0, 0
        for ban in match_data.get('bannedChampions', []):
            c_name = self.champ_dict.get(str(ban['championId']), "None")
            if ban['teamId'] == 100 and b_count < 5:
                blue_bans[b_count] = c_name
                b_count += 1
            elif ban['teamId'] == 200 and r_count < 5:
                red_bans[r_count] = c_name
                r_count += 1
        return blue_bans, red_bans

    # Initiate the checking logic as a function
    def _check_if_bot(self, champ_name, raw_team):
        for p in raw_team:
            if self.champ_dict.get(str(p['championId']), "Unknown") == champ_name:
                return p.get('bot', False) or not p.get('puuid')
        return False

    # Getting the Live game command.
    # Formats the team display strings.
    def _format_team_display(self, team_picks, raw_team):
        display = []
        for c in team_picks:
            meta_wr = self.ai.meta_db.get(c, 0.5000) * 100
            bot_tag = "🤖 " if self._check_if_bot(c, raw_team) else ""
            display.append(f"{bot_tag}{c} `[{meta_wr:.1f}%]`")
        return display

    # Fetches mastery and rank concurrently for a team.
    async def _fetch_team_stats(self, players, server):
        async def fetch_rank_safe(puuid):
            return await self.riot.get_summoner_rank(puuid, platform_override=server)

        wr_tasks = [fetch_rank_safe(puuid) for puuid, _, _ in players]
        mastery_tasks = [self.riot.get_champion_mastery(puuid, c_id, platform_override=server) for puuid, _, c_id in players]

        wr_results = await asyncio.gather(*wr_tasks)

        # Pause for exactly 1 second to let Riot's 20-per-second limit reset
        await asyncio.sleep(1.0)

        masteries = await asyncio.gather(*mastery_tasks)

        winrates = [parse_winrate(res) for res in wr_results]
        avg_wr = sum(winrates) / len(winrates) if winrates else 50.0

        return winrates, masteries, avg_wr

    # Predict the win condition before the game starts
    @app_commands.command(name="predict", description="Calculates win probability for a live match.")
    @app_commands.describe(
        server="The server region (e.g., NA1, EUW1, KR)",
        full_riot_id="The player's Riot ID (e.g., Doublelift#NA1)"
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    @app_commands.checks.cooldown(2, 5, key=lambda i: None)
    @app_commands.autocomplete(server=server_autocomplete)
    async def predict(self, interaction: discord.Interaction, server: str, full_riot_id: str):
        # Automatically gets "americas", "asia", or "europe"
        server = server.lower()
        if server not in self.server_dict:
            # We use ephemeral=True so only the user sees this error message
            await interaction.response.send_message(f"⚠️ Invalid server! Valid servers are: {', '.join(self.server_dict.keys())}", ephemeral=True)
            return

        region = self.server_dict[server]

        # This call out the Riot ID parser
        game_name, tag_line = parse_riot_id(full_riot_id)

        if not game_name:
            await interaction.response.send_message("⚠️ Format Error! Please use: `Name#Tag` (e.g., `Doublelift#NA1`)", ephemeral=True)
            return

        # Tell Discord to show the "Thinking..." status.
        await interaction.response.defer(thinking=True)

        try:
            # Get PUUID
            puuid = await self.riot.get_puuid(game_name, tag_line, region_override=region)
            if not puuid:
                await interaction.followup.send(f"⚠️ Could not find player {game_name} #{tag_line} on {server.upper()}. Check spelling!")
                return

            # Get Live Match
            match_data = await self.riot.get_live_match(puuid, platform_override=server)
            if not match_data:
                await interaction.followup.send("⚠️ This player is not currently in a live match!")
                return

            # Sort the teams
            raw_blue_team = [p for p in match_data['participants'] if p['teamId'] == 100]
            raw_red_team = [p for p in match_data['participants'] if p['teamId'] == 200]

            blue_picks = sort_team_roles(raw_blue_team, self.champ_dict, self.role_db)
            red_picks = sort_team_roles(raw_red_team, self.champ_dict, self.role_db)

            if len(blue_picks) < 5 or len(red_picks) < 5:
                await interaction.followup.send("⚠️ **Not enough players!** I only calculate full 5v5 matches.")
                return

            # Use our new helper to format the display!
            blue_display = self._format_team_display(blue_picks, raw_blue_team)
            red_display = self._format_team_display(red_picks, raw_red_team)

            # Get the Champion picks and set them in order
            draft_dict = {
                'blueTopChamp': blue_picks[0], 'blueJungleChamp': blue_picks[1], 'blueMiddleChamp': blue_picks[2],
                'blueADCChamp': blue_picks[3], 'blueSupportChamp': blue_picks[4],
                'redTopChamp': red_picks[0], 'redJungleChamp': red_picks[1], 'redMiddleChamp': red_picks[2],
                'redADCChamp': red_picks[3], 'redSupportChamp': red_picks[4]
            }

            # Calculate base probability
            base_blue_prob, _, blue_syn, red_syn = self.ai.predict_match(draft_dict)

            # Get PUUIDs, Summoner IDs, and Champion IDs for live scouting
            blue_players = [(p['puuid'], p.get('summonerId'), p['championId']) for p in raw_blue_team]
            red_players = [(p['puuid'], p.get('summonerId'), p['championId']) for p in raw_red_team]

            # Use our new helper to do the heavy asynchronous lifting!
            blue_winrates, blue_masteries, avg_blue_wr = await self._fetch_team_stats(blue_players, server)
            red_winrates, red_masteries, avg_red_wr = await self._fetch_team_stats(red_players, server)

            # Pass everything into the Hybrid Algorithm
            final_blue_prob, final_red_prob = self.ai.apply_hybrid_algorithm(
                base_blue_prob, blue_winrates, red_winrates, blue_masteries, red_masteries
            )

            # Send the results
            blue_embed, red_embed = build_predict_embeds(
                final_blue_prob, final_red_prob,
                avg_blue_wr, avg_red_wr,
                blue_syn, red_syn,
                blue_display, red_display
            )
            view = PredictView(blue_embed, red_embed)
            await interaction.followup.send(embed=blue_embed, view=view)

        # Error for Riot API issues, like if the servers are down or something.
        except aiohttp.ClientError:
            logger.error("Network error while connecting to Riot API in predict.")
            await interaction.followup.send("I couldn't connect to Riot's servers. They might be down or rate-limiting us!")

        # Catches if Riot suddenly changes their JSON format and a key goes missing
        except KeyError as e:
            logger.error(f"Missing expected data from Riot API in predict: {e}")
            await interaction.followup.send("Riot returned unexpected match data.")

    # Getting the enemy information.
    # Helper number one for fetching enemy data
    async def _fetch_single_enemy(self, c_name, riot_id, e_puuid, c_id, server, region):
        mastery_task = self.riot.get_champion_mastery(e_puuid, c_id, platform_override=server)
        # Fetch their last 5 ranked matches (costs 1 API call per player)
        history_task = self.riot.get_match_history(e_puuid, count=5, region_override=region)

        async def get_rank():
            await asyncio.sleep(1.5)
            return await self.riot.get_summoner_rank(e_puuid, platform_override=server)

        mastery, rank, history = await asyncio.gather(mastery_task, get_rank(), history_task)

        # Safety fallback if history fails to load
        if not isinstance(history, list):
            history = []

        return c_name, riot_id, rank, mastery, history

    # Helper number two for Duo detection
    @staticmethod
    def _find_duos(player_histories: list) -> set:
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

    # Initiate fetching enemy data as a function, this is where we get the mastery, rank, and match history for each enemy player, and also check if any of them are duos.
    async def _fetch_enemy_data(self, match_data, enemy_team_id, server, region):
        bot_entries = []
        player_tasks = []

        for p in match_data['participants']:
            if p['teamId'] == enemy_team_id:
                c_name = self.champ_dict.get(str(p['championId']), 'Unknown')
                e_puuid = p.get('puuid')

                if p.get('bot', False) or not e_puuid:
                    bot_entries.append(c_name)
                else:
                    riot_id = p.get('riotId') or p.get('summonerName') or 'Unknown Player'
                    player_tasks.append(
                        self._fetch_single_enemy(c_name, riot_id, e_puuid, p['championId'], server, region))

        # Wait for all players to finish fetching
        raw_results = await asyncio.gather(*player_tasks)

        # Extract just the IDs and Histories to pass to our Duo Detective
        histories = [(res[1], res[4]) for res in raw_results]
        duo_set = DraftCommands._find_duos(histories)

        # Build the final list to send to the embed formatter
        final_players = []
        for c_name, riot_id, rank, mastery, _ in raw_results:
            is_duo = riot_id in duo_set  # True if the Detective found them in the set
            final_players.append((c_name, riot_id, rank, mastery, is_duo))

        return bot_entries, final_players

    # This part checks what type of bs the enemy team is running
    @app_commands.command(name="scout", description="Builds an enemy dossier for a live match.")
    @app_commands.describe(
        server="The server region (e.g., NA1, EUW1, KR)",
        full_riot_id="The player's Riot ID (e.g., Doublelift#NA1)"
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    @app_commands.checks.cooldown(2, 5, key=lambda i: None)
    @app_commands.autocomplete(server=server_autocomplete)
    async def scout(self, interaction: discord.Interaction, server: str, full_riot_id: str):
        # Automatically gets "americas", "asia", or "europe"
        server = server.lower()
        if server not in self.server_dict:
            await interaction.response.send_message(f"⚠️ Invalid server! Valid servers are: {', '.join(self.server_dict.keys())}", ephemeral=True)
            return

        region = self.server_dict[server]

        # This call out the Riot ID parser
        game_name, tag_line = parse_riot_id(full_riot_id)

        # Same as above bouncer, yeah yeah yeah.
        if not game_name:
            await interaction.response.send_message("⚠️ Format Error! Please use: `Name#Tag` (e.g., `Doublelift#NA1`)", ephemeral=True)
            return

        # Tell Discord to show the "Thinking..." status.
        await interaction.response.defer(thinking=True)

        try:
            safe_name = escape_mentions(game_name)
            # This call out get_riot_puuid function from RiotAPIClient Class in riot_api.py.
            puuid = await self.riot.get_puuid(game_name, tag_line, region_override=region)
            if not puuid:
                # Since we deferred above, we MUST use followup.send() from here on out!
                await interaction.followup.send(f"⚠️ Could not find player {safe_name} #{tag_line} on {server.upper()}. Check spelling!")
                return

            # This call out get_live_match function from RiotAPIClient Class in riot_api.py.
            match_data = await self.riot.get_live_match(puuid, platform_override=server)
            if not match_data:
                await interaction.followup.send("⚠️ This player is not currently in a live match!")
                return

            # Figures which team the current user is on Blue or Red.
            user_team = next((p['teamId'] for p in match_data['participants'] if p['puuid'] == puuid), None)
            if not user_team:
                await interaction.followup.send("⚠️ Could not locate user in match data.")
                return

            # Building the Discord Embed
            enemy_team_id = 200 if user_team == 100 else 100
            bot_entries, player_results = await self._fetch_enemy_data(match_data, enemy_team_id, server, region)
            embed = build_scout_embed(server, safe_name, bot_entries, player_results, self.ai.meta_db)

            await interaction.followup.send(embed=embed)

        # Error for Riot API issues, like if the servers are down or something.
        except aiohttp.ClientError:
            logger.error("Network error while connecting to Riot API in scout.")
            await interaction.followup.send("I couldn't connect to Riot's servers. They might be down or rate-limiting us!")

        # Catches if Riot suddenly changes their JSON format and a key goes missing
        except KeyError as e:
            logger.error(f"Missing expected data from Riot API in scout: {e}")
            await interaction.followup.send("Riot returned unexpected match data.")

# Setup Hook or something whatever this is called.
async def setup(bot):
    await bot.add_cog(DraftCommands(bot, bot.riot_client, bot.ai_system, bot.meta_db, bot.champ_dict, bot.role_db))