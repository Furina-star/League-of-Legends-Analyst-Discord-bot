"""
This part of the Discord  League Analyst Bot
is all about general commands,
commands that are common between Discord Bots.
"""

import discord
from discord.ext import commands


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def ping(self, ctx):
        await ctx.send("🏓 I'm online and ready to analyze!")

    @commands.command(name="help")
    @commands.cooldown(1, 1, commands.BucketType.user)
    async def custom_help(self, ctx):
        embed = discord.Embed(
            title="💧 Furina League Analyst Bot - Help Menu",
            description="I am Furina, your personal Solo Queue analyst! Here is how to use my commands:\n"
                        "Prefix: `f` or `furina` (e.g., `f ping`, `f predict`)",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🏓 `f ping`",
            value="Checks if Furina is online.",
            inline=False
        )
        embed.add_field(
            name="⚔️ `f predict`",
            value="Calculates win probability for a live match.\n"
                  "**Format:** `f predict <server> Name#Tag`\n"
                  "**Example:** `f predict KR Hide on bush#KR1`",
            inline=False
        )
        embed.add_field(
            name="🕵️ `f scout`",
            value="Builds an enemy dossier for a live match.\n"
                  "**Format:** `f scout <server> Name#Tag`\n"
                  "**Example:** `f scout NA1 Doublelift#NA1`",
            inline=False
        )
        embed.set_footer(
            text="Valid servers: NA1, EUW1, EUN1, KR, SG2, TW2, VN2, TH2, PH2, BR1, LAN1, LAS1, OC1, TR1, RU"
        )

        await ctx.send(embed=embed)


# Setup hook to load the Cog
async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))