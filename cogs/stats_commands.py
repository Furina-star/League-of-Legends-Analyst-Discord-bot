"""
This cog is responsible for handling stats related commands
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from modules.utils.parsers import parse_riot_id, extract_postgame_stats
from modules.interface.embed_formatter import build_lastgame_embed
from modules.interface.discord_helpers import server_autocomplete
from modules.interface.views import MatchCycleView
from modules.utils.state_resolvers import resolve_match_eligibility
from utils.database_manager import DatabaseManager

# Get the logging system
logger = logging.getLogger("discord")

class StatsCommands(commands.Cog):
    def __init__(self, bot, riot_client, server_dict):
        self.bot = bot
        self.riot = riot_client
        self.server_dict = server_dict
        self.db = DatabaseManager()

    # Getting the last game or post match review command
    # Identify what the player did after the game.
    @app_commands.command(name="postgame", description="Furina ruthlessly analyzes your most recent match.")
    @app_commands.describe(server="The server region (e.g., NA1, EUW1, KR)", full_riot_id="The player's Riot ID (e.g., Doublelift#NA1)")
    @app_commands.checks.cooldown(1, 2, key=lambda i: i.user.id)
    @app_commands.autocomplete(server=server_autocomplete)
    async def postgame(self, interaction: discord.Interaction, server: str, full_riot_id: str):
        # Automatically gets "americas", "asia", or "europe"
        server = server.lower()
        if server not in self.server_dict:
            # We use ephemeral=True so only the user sees this error message
            await interaction.response.send_message(
                f"⚠️ Invalid server! Valid servers are: {', '.join(self.server_dict.keys())}", ephemeral=True)
            return

        region = self.server_dict[server]

        # This call out the Riot ID parser
        game_name, tag_line = parse_riot_id(full_riot_id)

        if not game_name:
            await interaction.response.send_message(
                "⚠️ Format Error! Please use: `Name#Tag` (e.g., `Doublelift#NA1`)", ephemeral=True)
            return

        # Tell Discord to show the "Thinking..." status.
        await interaction.response.defer(thinking=True)

        try:
            # Get the puuid
            puuid = await self.riot.get_puuid(game_name, tag_line, region_override=region)
            if not puuid:
                await interaction.followup.send(
                    "⚠️ Could not find player. Check spelling!",allowed_mentions=discord.AllowedMentions.none())
                return

            # Get the most recent match ID
            history = await self.riot.get_match_history(puuid, count=10, region_override=region, server_context=server)
            if not history:
                await interaction.followup.send("⚠️ This player has no recent games.")
                return

            match_data = await self.riot.get_match_details(history[0], region_override=region, server_context=server)
            if not match_data:
                await interaction.followup.send("⚠️ Could not fetch match details for this game.")
                return

            # Find the player's stats in the match data, map the queue ID, and calculate the total kills for that team
            player_stats = extract_postgame_stats(match_data, puuid, history[0])

            if not player_stats:
                await interaction.followup.send("⚠️ Error parsing player data.")
                return

            # Inject the data into the database for the Hall of Shame
            try:
                # Get the queue type and duration from the raw match info
                queue_id = match_data.get('info', {}).get('queueId', 0)
                game_duration = match_data.get('info', {}).get('gameDuration', 0)
                is_eligible, _ = resolve_match_eligibility(game_duration, queue_id)

                if is_eligible:
                    db_manager = self.bot.get_cog("GeneralCommands").db
                    linked_discord_id = await db_manager.get_discord_id_by_puuid(puuid)

                    if linked_discord_id:
                        challenges = player_stats.get('challenges', {})
                        await db_manager.log_match(
                            discord_id=linked_discord_id,
                            match_id=history[0],
                            kp=challenges.get('killParticipation', 0),
                            deaths=player_stats.get('deaths', 0),
                            gpm=challenges.get('goldPerMinute', 0),
                            dpm=challenges.get('damagePerMinute', 0),
                            win=player_stats.get('win', False)
                        )
            except Exception as e:
                logger.error(f"Hall of Shame DB Error: {e}")

            # Build the embed and send the Roast/Praise embed
            embed = build_lastgame_embed(server, full_riot_id, player_stats, self.bot.patch_version)
            view = MatchCycleView(self.riot, puuid, server, region, history, 0, self.bot.patch_version, full_riot_id)
            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Error in lastgame command: {e}")
            await interaction.followup.send("⚠️ A critical error occurred while fetching the match data.")

async def setup(bot):
    await bot.add_cog(StatsCommands(bot, bot.riot_client, bot.server_dict))