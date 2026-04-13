"""
This is where helper functions related to Discord interactions go, such as autocomplete functions for slash command options.
"""

import discord
from discord import app_commands
from discord.app_commands import Choice

# This is the autocomplete function for server selection in slash commands.
async def server_autocomplete(interaction: discord.Interaction, current: str) -> list[Choice[str]]: # noqa
    servers = list(interaction.client.server_dict.keys())

    choices = [
        app_commands.Choice(name=server.upper(), value=server.upper())
        for server in servers if current.lower() in server.lower()
    ]
    return choices[:25]