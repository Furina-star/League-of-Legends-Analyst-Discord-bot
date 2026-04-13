"""
This cog is responsible for handling commands regarding about leaderboards and such.
Adding more future implementation I hope.
"""

import discord
from discord.ext import commands
from discord import app_commands

class LeaderboardCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hallofshame", description="View the server's worst League of Legends performers this week.")
    @app_commands.checks.cooldown(1, 2, key=lambda i: i.user.id)
    async def hallofshame(self, interaction: discord.Interaction):
        await interaction.response.defer()

        stats = await self.bot.db.get_hall_of_shame()

        embed = discord.Embed(
            title="🏛️ The Hall of Shame",
            description="The Oratrice has compiled the server's most tragic performances.",
            color=discord.Color.dark_theme()
        )

        has_data = False

        if stats["backpack"]:
            has_data = True
            embed.add_field(
                name="💀 The Heavy Backpack (Lowest KP%)",
                value=f"<@{stats['backpack'][0]}> averaged an abysmal **{stats['backpack'][1] * 100:.1f}%** Kill Participation.",
                inline=False
            )

        if stats["jester"]:
            has_data = True
            embed.add_field(
                name="🤡 The Court Jester (Most Deaths)",
                value=f"<@{stats['jester'][0]}> managed to die **{stats['jester'][1]}** times in a single match.",
                inline=False
            )

        if stats["tax"]:
            has_data = True
            embed.add_field(
                name="💰 The Tax Collector (Highest GPM)",
                value=f"<@{stats['tax'][0]}> hoarded **{stats['tax'][1]:.0f}** Gold Per Minute, actively doing nothing with it.",
                inline=False
            )

        if not has_data:
            embed.description = "The stage is currently empty. Play more games this week to populate the Hall of Shame."

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LeaderboardCommands(bot))