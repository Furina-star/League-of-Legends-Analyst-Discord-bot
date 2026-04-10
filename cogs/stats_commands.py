"""
This is the '/ last game' or post game review command.
"""

import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
import logging
from utils.parsers import parse_riot_id
from utils.embed_formatter import build_lastgame_embed

# Get the logging system
logger = logging.getLogger("discord")

class StatsCommands(commands.Cog):
    def __init__(self, bot, riot_client, server_dict):
        self.bot = bot
        self.riot = riot_client
        self.server_dict = server_dict

    # Same as in draft_commands might be breaking DRY rules
    async def server_autocomplete(self, interaction: discord.Interaction, current: str) -> list[Choice[str | int | float]]:
        servers = list(self.server_dict.keys())
        choices = [
            app_commands.Choice(name=server.upper(), value=server.upper())
            for server in servers if current.lower() in server.lower()
        ]
        return choices[:25]

    # Getting the last game or post match review command
    # Identify what the player did after the game.
    @app_commands.command(name="postgame", description="Furina ruthlessly analyzes your most recent match.")
    @app_commands.describe(
        server="The server region (e.g., NA1, EUW1, KR)",
        full_riot_id="The player's Riot ID (e.g., Doublelift#NA1)"
    )
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
            await interaction.response.send_message("⚠️ Format Error! Please use: `Name#Tag` (e.g., `Doublelift#NA1`)",ephemeral=True)
            return

        # Tell Discord to show the "Thinking..." status.
        await interaction.response.defer(thinking=True)

        try:
            # Get the puuid
            puuid = await self.riot.get_puuid(game_name, tag_line, region_override=region)
            if not puuid:
                await interaction.followup.send(f"⚠️ Could not find player {game_name}#{tag_line} on {server.upper()}. Check spelling!",allowed_mentions=discord.AllowedMentions.none())
                return

            # Get the most recent match ID
            history = await self.riot.get_match_history(puuid, count=1, region_override=region)
            if not history:
                await interaction.followup.send("⚠️ This player has no recent games.")
                return
            match_id = history[0]

            # Get the match details
            match_data = await self.riot.get_match_details(match_id, region_override=region)
            if not match_data:
                await interaction.followup.send("⚠️ This player is not currently in a live match!")
                return

            # Find the player's stats in the match data
            player_stats = None
            for participant in match_data['info']['participants']:
                if participant['puuid'] == puuid:
                    # Attach game duration to the stats dict so the Roast Engine can see it
                    participant['gameDuration'] = match_data['info']['gameDuration']
                    player_stats = participant
                    break

            if not player_stats:
                await interaction.followup.send("⚠️ Error parsing player data.")
                return

            # Build the embed and send the Roast/Praise embed
            embed = build_lastgame_embed(server, full_riot_id, player_stats)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in lastgame command: {e}")
            await interaction.followup.send("⚠️ A critical error occurred while fetching the match data.")

async def setup(bot):
    await bot.add_cog(StatsCommands(bot, bot.riot_client, bot.server_dict))