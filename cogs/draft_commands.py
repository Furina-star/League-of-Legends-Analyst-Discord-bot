"""
This part of the Discord  League Analyst Bot
is all about the draft commands,
commands that analyze the live game, predict the win condition, and scout the enemy team.
"""
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
import logging
from utils.embed_formatter import build_predict_embeds, build_scout_embed
from utils.views import PredictView
from discord.utils import escape_mentions
from utils.parsers import parse_riot_id, sort_team_roles, format_team_display
from utils.discord_helpers import server_autocomplete

# Get the logging system
logger = logging.getLogger(__name__)

# Cog Class
class DraftCommands(commands.Cog):
    def __init__(self, bot, riot_client, ai_system, meta_db, champ_dict, role_db, keystone_db):
        # Store everything here to use for the bot commands yeah yessir.
        self.bot = bot
        self.riot = riot_client
        self.ai = ai_system
        self.meta_db = meta_db
        self.champ_dict = champ_dict
        self.server_dict = bot.server_dict
        self.role_db = role_db
        self.keystone_db = keystone_db

    # Getting the Live game command.
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
                await interaction.followup.send(f"⚠️ Could not find player {game_name}#{tag_line} on {server.upper()}. Check spelling!",allowed_mentions=discord.AllowedMentions.none())
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
            blue_display = format_team_display(blue_picks, raw_blue_team, self.meta_db, self.champ_dict)
            red_display = format_team_display(red_picks, raw_red_team, self.meta_db, self.champ_dict)

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
            blue_winrates, blue_masteries, avg_blue_wr = await self.riot._fetch_team_stats(blue_players, server)
            red_winrates, red_masteries, avg_red_wr = await self.riot._fetch_team_stats(red_players, server)

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
                await interaction.followup.send(f"⚠️ Could not find player {game_name}#{tag_line} on {server.upper()}. Check spelling!", allowed_mentions=discord.AllowedMentions.none())
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
            bot_entries, player_results = await self.riot._fetch_enemy_data(
                match_data, enemy_team_id, server, region, self.champ_dict, self.keystone_db, self.role_db
            )
            embed = build_scout_embed(server, safe_name, bot_entries, player_results, self.ai.meta_db)

            await interaction.followup.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

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
    await bot.add_cog(DraftCommands(bot, bot.riot_client, bot.ai_system, bot.meta_db, bot.champ_dict, bot.role_db, bot.keystone_db))