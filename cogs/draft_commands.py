"""
This part of the Discord  League Analyst Bot
is all about the draft commands,
commands that analyze the live game, predict the win condition, and scout the enemy team.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from modules.interface.embed_formatter import build_predict_embed, build_scout_embed, build_draft_embed
from modules.interface.views import LiveDraftDashboard
from discord.utils import escape_mentions
from modules.utils.parsers import parse_riot_id, sort_team_roles, extract_live_player_names
from modules.interface.discord_helpers import server_autocomplete
from modules.interface.canvas_engine import render_draft_board
from discord.app_commands import locale_str as _
from modules.utils.constants import CMD_PREDICT, DESC_PREDICT, CMD_SCOUT, DESC_SCOUT, ARG_REGION, ARG_RIOT_ID, CMD_COACH, DESC_COACH

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
    @app_commands.command(name=_(CMD_PREDICT), description=_(DESC_PREDICT))
    @app_commands.describe(server=_(ARG_REGION), full_riot_id=_(ARG_RIOT_ID))
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

        # This call out the Riot ID parser
        game_name, tag_line = parse_riot_id(full_riot_id)
        if not game_name or not tag_line:
            await interaction.response.send_message("⚠️ Format Error! You must include the hashtag. Example: `Doublelift#NA1`", ephemeral=True)
            return

        # Tell Discord to show the "Thinking..." status.
        await interaction.response.defer(thinking=True)

        # Get PUUID
        puuid = await self.riot.get_puuid(game_name, tag_line, server_context=server)
        if not puuid:
            await interaction.followup.send(f"⚠️ Could not find player {game_name}#{tag_line}.", allowed_mentions=discord.AllowedMentions.none())
            return

        # Get Live Match
        match_data = await self.riot.get_live_match(puuid, platform_override=server)
        if not match_data:
            await interaction.followup.send("⚠️ Could not fetch match data! The player is either not in a live match, or Riot's servers are currently down.")
            return

        # Sort the teams
        raw_blue_team = [p for p in match_data['participants'] if p['teamId'] == 100]
        raw_red_team = [p for p in match_data['participants'] if p['teamId'] == 200]

        blue_picks = sort_team_roles(raw_blue_team, self.champ_dict, self.role_db)
        red_picks = sort_team_roles(raw_red_team, self.champ_dict, self.role_db)

        if len(blue_picks) < 5 or len(red_picks) < 5:
            await interaction.followup.send("⚠️ **Not enough players!** I only calculate full 5v5 matches.")
            return

        # Get the Champion picks and set them in order
        draft_dict = {
            'blueTopChamp': blue_picks[0], 'blueJungleChamp': blue_picks[1], 'blueMiddleChamp': blue_picks[2],
            'blueADCChamp': blue_picks[3], 'blueSupportChamp': blue_picks[4],
            'redTopChamp': red_picks[0], 'redJungleChamp': red_picks[1], 'redMiddleChamp': red_picks[2],
            'redADCChamp': red_picks[3], 'redSupportChamp': red_picks[4]
        }

        # Calculate base probability
        base_blue_prob, _, blue_syn, red_syn = await asyncio.to_thread(self.ai.predict_match, draft_dict)

        # Get PUUIDs, Summoner IDs, and Champion IDs for live scouting
        blue_players = [(p['puuid'], p.get('summonerId'), p['championId']) for p in raw_blue_team]
        red_players = [(p['puuid'], p.get('summonerId'), p['championId']) for p in raw_red_team]

        # Use our new helper to do the heavy asynchronous lifting!
        blue_winrates, _, avg_blue_wr = await self.riot.fetch_team_stats(blue_players, server)
        red_winrates, _, avg_red_wr = await self.riot.fetch_team_stats(red_players, server)

        # Pass everything into the Hybrid Algorithm
        final_blue_prob, final_red_prob = await asyncio.to_thread(self.ai.apply_hybrid_algorithm, base_blue_prob, blue_winrates, red_winrates)

        # Send the results
        positions = ['top', 'jungle', 'mid', 'adc', 'support']
        blue_dict = dict(zip(positions, blue_picks))
        red_dict = dict(zip(positions, red_picks))

        # Map the extracted names to standard positions
        blue_names = dict(zip(positions, extract_live_player_names(blue_picks, raw_blue_team, self.champ_dict)))
        red_names = dict(zip(positions, extract_live_player_names(red_picks, raw_red_team, self.champ_dict)))

        image_buffer = await render_draft_board(
            blue_dict=blue_dict,
            red_dict=red_dict,
            role="None",
            user_team="None",
            banned_champs=None,
            blue_names=blue_names,
            red_names=red_names,
            blue_prob=final_blue_prob,
            red_prob=final_red_prob,
            bg_filename="predict_bg.jpg"  # Background Image
        )

        file = discord.File(fp=image_buffer, filename="draft_board.png")
        embed = build_predict_embed(
            final_blue_prob, final_red_prob,
            avg_blue_wr, avg_red_wr,
            blue_syn, red_syn,
            match_data
        )

        await interaction.followup.send(embed=embed, file=file)

    # Getting the enemy information.
    # This part checks what type of bs the enemy team is running
    @app_commands.command(name=_(CMD_SCOUT), description=_(DESC_SCOUT))
    @app_commands.describe(server=_(ARG_REGION), full_riot_id=_(ARG_RIOT_ID))
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    @app_commands.checks.cooldown(2, 5, key=lambda i: None)
    @app_commands.autocomplete(server=server_autocomplete)
    async def scout(self, interaction: discord.Interaction, server: str, full_riot_id: str):
        # Automatically gets "americas", "asia", or "europe"
        server = server.lower()
        if server not in self.server_dict:
            await interaction.response.send_message(f"⚠️ Invalid server! Valid servers are: {', '.join(self.server_dict.keys())}", ephemeral=True)
            return

        # This call out the Riot ID parser
        game_name, tag_line = parse_riot_id(full_riot_id)
        if not game_name or not tag_line:
            await interaction.response.send_message("⚠️ Format Error! You must include the hashtag. Example: `Doublelift#NA1`", ephemeral=True)
            return

        # Tell Discord to show the "Thinking..." status.
        await interaction.response.defer(thinking=True)


        safe_name = escape_mentions(game_name)
        # This call out get_riot_puuid function from RiotAPIClient Class in riot_api.py.
        puuid = await self.riot.get_puuid(game_name, tag_line, server_context=server)
        if not puuid:
            await interaction.followup.send(f"⚠️ Could not find player {game_name}#{tag_line}.", allowed_mentions=discord.AllowedMentions.none())
            return

        # This call out get_live_match function from RiotAPIClient Class in riot_api.py.
        match_data = await self.riot.get_live_match(puuid, platform_override=server)
        if not match_data:
            await interaction.followup.send("⚠️ Could not fetch match data! The player is either not in a live match, or Riot's servers are currently down.")
            return

        # Figures which team the current user is on Blue or Red.
        user_team = next((p['teamId'] for p in match_data['participants'] if p['puuid'] == puuid), None)
        if not user_team:
            await interaction.followup.send("⚠️ Could not locate user in match data.")
            return

        # Building the Discord Embed
        enemy_team_id = 200 if user_team == 100 else 100
        bot_entries, player_results = await self.riot.fetch_enemy_data(
            match_data, enemy_team_id, server, self.champ_dict, self.keystone_db, self.role_db
        )

        embed = build_scout_embed(server, safe_name, bot_entries, player_results, self.ai.meta_db)

        await interaction.followup.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    # A draft pick coach
    # This is where it suggests champions based on current draft picks
    @app_commands.command(name=_(CMD_COACH), description=_(DESC_COACH))
    @app_commands.choices(
        role=[
            app_commands.Choice(name="Top", value="top"),
            app_commands.Choice(name="Jungle", value="jungle"),
            app_commands.Choice(name="Mid", value="mid"),
            app_commands.Choice(name="ADC", value="adc"),
            app_commands.Choice(name="Support", value="support"),
        ],
        team=[
            app_commands.Choice(name="Blue", value="blue"),
            app_commands.Choice(name="Red", value="red"),
        ]
    )
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def coach(self, interaction: discord.Interaction, role: app_commands.Choice[str],
                    team: app_commands.Choice[str]):
        await interaction.response.defer()

        # Initialize empty state
        empty_dict = dict.fromkeys(['top', 'jungle', 'mid', 'adc', 'support'], "Unknown")
        user_team_str = team.value.title()

        # Spawn the view
        dashboard = LiveDraftDashboard(self.ai, role.value, user_team_str, self.role_db, self.champ_dict)

        # Run first prediction
        top_picks = await asyncio.to_thread(self.ai.suggest_champion, role.value, user_team_str, empty_dict, empty_dict, self.role_db, [])

        # Call the centralized formatter!
        embed = build_draft_embed(
            role=role.value,
            user_team=user_team_str,
            error_msg=None,
            top_picks=top_picks,
            blue_dict=empty_dict,
            red_dict=empty_dict,
            role_db=self.role_db,
        )

        image_buffer = await render_draft_board(
            blue_dict=empty_dict,
            red_dict=empty_dict,
            role=role.value,
            user_team=user_team_str,
            banned_champs = []
        )
        file = discord.File(fp=image_buffer, filename="draft_board.png")

        await interaction.followup.send(embed=embed, view=dashboard, file=file)

# Setup Hook or something whatever this is called.
async def setup(bot):
    await bot.add_cog(DraftCommands(bot, bot.riot_client, bot.ai_system, bot.meta_db, bot.champ_dict, bot.role_db, bot.keystone_db))