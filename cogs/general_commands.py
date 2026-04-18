"""
This part of the Discord  League Analyst Bot
is all about general commands,
commands that are common between Discord Bots.
"""

import discord
import random
import asyncio
import aiosqlite
import logging
from discord.ext import commands
from discord import app_commands
from modules.interface.embed_formatter import build_help_embed
from modules.interface.discord_helpers import server_autocomplete
from modules.interface.views import HelpPaginationView
from modules.persona.verdicts import GUILTY_TEMPLATES, PLOT_TWIST_TEMPLATES, MERCY_TEMPLATES, SENTENCE_TEMPLATES
from modules.utils.state_resolvers import resolve_link_state
from discord.app_commands import locale_str as _
from modules.utils.constants import (
    CMD_LINK, DESC_LINK, CMD_UNLINK, DESC_UNLINK,
    ARG_RIOT_ID, ARG_REGION, CMD_PING, DESC_PING,
    CMD_HELP, DESC_HELP, CMD_TRIAL, DESC_TRIAL,
    ARG_MATCH_INDEX,CMD_CONFESS, DESC_CONFESS,
    ARG_SIN
)

# Get the logger system
logger = logging.getLogger("discord")

class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guilty_deck = []
        self.plot_twist_deck = []
        self.mercy_deck = []
        self.sentence_deck = []

    # The Master Card Drawer, helper to refill, shuffle, and format a card from a deck
    def _draw_verdict(self, deck_name: str, templates: list, **kwargs) -> str:
        deck = getattr(self, deck_name)
        if not deck:
            deck.extend(templates)
            random.shuffle(deck)

        # Pop the template and instantly format it with the passed variables
        return deck.pop(0).format(**kwargs)

    # The ping command
    @app_commands.command(name=_(CMD_PING), description=_(DESC_PING))
    async def ping(self, interaction: discord.Interaction):
        # Calculate the latency in milliseconds
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"I'm online and ready to analyze! **Latency: {latency}ms**.")

    # The help command
    # Utilizes a page cycle system with buttons, and a single embed that gets edited with new content on each page turn.
    @app_commands.command(name=_(CMD_HELP), description=_(DESC_HELP))
    @app_commands.checks.cooldown(1, 2, key=lambda i: i.user.id)
    async def help_command(self, interaction: discord.Interaction):
        # Initialize the view and the first page of the embed
        view = HelpPaginationView()
        embed = build_help_embed(page=0)

        # Send the interactive menu
        await interaction.response.send_message(embed=embed, view=view)

    # The Trial command
    # What does it do? put the victim in trial and let furina judge for fun.
    @app_commands.command(name=_(CMD_TRIAL), description=_(DESC_TRIAL))
    @app_commands.describe(defendant=_(ARG_MATCH_INDEX))
    @app_commands.checks.cooldown(1, 2, key=lambda i: i.user.id)
    async def trial(self, interaction: discord.Interaction, defendant: discord.Member):

        await interaction.response.send_message(f"⚖️ **The court is now in session!**\n{interaction.user.mention} accuses {defendant.mention} of atrocious gameplay.")

        await asyncio.sleep(2)
        spinning_msg = await interaction.followup.send("⚙️ *The Oratrice Mecanique d'Analyse Cardinale is spinning...*", wait=True)
        await asyncio.sleep(3)

        if random.choice([True, False]):
            verdict = self._draw_verdict("guilty_deck", GUILTY_TEMPLATES, user=interaction.user.mention, defendant=defendant.mention)
            color = discord.Color.red()
        else:
            verdict = self._draw_verdict("plot_twist_deck", PLOT_TWIST_TEMPLATES, user=interaction.user.mention,defendant=defendant.mention)
            color = discord.Color.blue()

        await spinning_msg.edit(content=None, embed=discord.Embed(title="📜 Final Verdict", description=verdict, color=color))

    # The Confess command
    # What does it do? the victim can plead again
    @app_commands.command(name=_(CMD_CONFESS), description=_(DESC_CONFESS))
    @app_commands.describe(crime=_(ARG_SIN))
    async def confess(self, interaction: discord.Interaction, crime: str):
        await interaction.response.send_message(f"🙏 {interaction.user.mention} has approached the stand to confess: **\"{crime}\"**")

        await asyncio.sleep(3)
        msg = await interaction.followup.send("⚙️ *The Oratrice Mecanique d'Analyse Cardinale is evaluating your sincerity...*", wait=True)
        await asyncio.sleep(4)

        if random.choice([True, False]):
            verdict = self._draw_verdict("mercy_deck", MERCY_TEMPLATES, crime=crime)
            color = discord.Color.green()
        else:
            verdict = self._draw_verdict("sentence_deck", SENTENCE_TEMPLATES, crime=crime)
            color = discord.Color.red()

        await msg.edit(content=None, embed=discord.Embed(title="📜 Final Judgment", description=verdict, color=color))

    # The Link Command
    # This is where it links Riot PUUID to Discord ID, so we can track their games and stats.
    @app_commands.command(name=CMD_LINK, description=DESC_LINK)
    @app_commands.describe(server=ARG_REGION, full_riot_id=ARG_RIOT_ID)
    @app_commands.checks.cooldown(1, 2, key=lambda i: i.user.id)
    @app_commands.autocomplete(server=server_autocomplete)
    async def link(self, interaction: discord.Interaction, server: str, full_riot_id: str):
        await interaction.response.defer(ephemeral=True)

        # The Guard Clause, fail fast before doing any heavy lifting
        if "#" not in full_riot_id:
            return await interaction.followup.send("⚠️ Invalid format. You must include the hashtag (e.g., Name#Tag).")

        stats_cog = self.bot.get_cog("StatsCommands")
        if not stats_cog:
            return await interaction.followup.send("⚠️ Critical Error: Stats module is currently offline.")

        server = server.lower()
        if server not in stats_cog.server_dict:
            return await interaction.followup.send("⚠️ Invalid server region.")

        game_name, tag_line = full_riot_id.split("#", 1)
        new_riot_id = f"{game_name}#{tag_line}"

        try:
            # API Validation
            puuid = await stats_cog.riot.get_puuid(game_name, tag_line, server_context=server)
            if not puuid:
                return await interaction.followup.send(
                    "⚠️ Could not find that Riot ID. Ensure the spelling and region are correct.")

            # Anti-Fraud Validation
            existing_owner = await self.bot.db.get_discord_id_by_puuid(puuid)
            if existing_owner and str(existing_owner) != str(interaction.user.id):
                return await interaction.followup.send(
                    f"⚠️ Identity theft is a serious crime! That Riot ID is already claimed by <@{existing_owner}>.")

            # Call the helper from state_resolvers.py
            should_abort, msg = await resolve_link_state(self.bot.db, interaction.user.id, puuid, new_riot_id)

            if should_abort:
                return await interaction.followup.send(msg)

            # Database execution
            await self.bot.db.link_account(interaction.user.id, puuid, new_riot_id, server)
            await interaction.followup.send(msg)


        except aiosqlite.Error as db_err:
            logger.error(f"Database error in /link: {db_err}")
            await interaction.followup.send("⚠️ A database error occurred")

        except Exception as e:
            logger.error(f"Unexpected error in /link: {e}", exc_info=True)
            await interaction.followup.send("⚠️ An unexpected error occurred while contacting the Riot servers.")

    # The Unlink Command
    # Unlink the Riot ID from the Discord User
    @app_commands.command(name=CMD_UNLINK, description=DESC_UNLINK)
    @app_commands.checks.cooldown(1, 2, key=lambda i: i.user.id)
    async def unlink(self, interaction: discord.Interaction):
        try:
            current_link = await self.bot.db.get_linked_account(interaction.user.id)
            if not current_link:
                await interaction.response.send_message( "⚠️ You don't have an account linked to the Oratrice. You are already free.", ephemeral=True)
                return

            await self.bot.db.unlink_account(interaction.user.id)
            await interaction.response.send_message(f"✅ Your account (**{current_link[0]}**) has been successfully unlinked. The Oratrice will no longer track your performances.", ephemeral=True)

        except aiosqlite.Error as db_err:
            logger.error(f"Database error in /unlink for {interaction.user}: {db_err}")
            await interaction.response.send_message("⚠️ A database error occurred. You are trapped in the Hall of Shame for now.", ephemeral=True)

# Setup hook to load the Cog
async def setup(bot):
    cog = GeneralCommands(bot)
    await bot.add_cog(cog)