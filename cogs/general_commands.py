"""
This part of the Discord  League Analyst Bot
is all about general commands,
commands that are common between Discord Bots.
"""

import discord
from discord.ext import commands
from discord import app_commands
from modules.interface.embed_formatter import build_help_embed
import random
import asyncio

class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guilty_deck = []
        self.plot_twist_deck = []
        self.mercy_deck = []
        self.sentence_deck = []

    # The ping command
    @app_commands.command(name="ping", description="Checks if Furina is online and functioning.")
    async def ping(self, interaction: discord.Interaction):
        # Calculate the latency in milliseconds
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"I'm online and ready to analyze! **Latency: {latency}ms**.")

    # The help command
    @app_commands.command(name="help", description="Displays the Furina League Analyst help menu.")
    async def help_command(self, interaction: discord.Interaction):
        embed = build_help_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # The Trial command
    # What does it do? put the victim in trial and let furina judge for fun.
    @app_commands.command(name="trial", description="Judge who truly threw the game and deliver a final verdict.")
    @app_commands.describe(defendant="The duo partner you are accusing.")
    async def trial(self, interaction: discord.Interaction, defendant: discord.Member):
        # Open the Court Session
        await interaction.response.send_message(f"⚖️ **The court is now in session!**\n{interaction.user.mention} accuses {defendant.mention} of atrocious gameplay.")

        # Build the suspense lol
        await asyncio.sleep(2)
        spinning_msg = await interaction.followup.send("⚙️ *The Oratrice Mecanique d'Analyse Cardinale is spinning...*",wait=True)
        await asyncio.sleep(3)

        is_guilty = random.choice([True, False])

        if is_guilty:
            if not self.guilty_deck:
                self.guilty_deck = [
                    f"**GUILTY!** {defendant.mention}, your mechanical incompetence is an insult to the stage! {interaction.user.mention} is absolved of all blame.",
                    f"**CONVICTED!** The evidence is overwhelming. {defendant.mention} was playing with their eyes closed! {interaction.user.mention} is the true victim here.",
                    f"**SENTENCED!** {defendant.mention}, your 'gameplay' is a comedy of errors. The Oratrice rules in favor of {interaction.user.mention}!",
                    f"**VERDICT: ATROCIOUS!** {defendant.mention}, I've seen more coordination from a newborn hilichurl. {interaction.user.mention} is innocent!",
                    f"**EXPOSED!** {defendant.mention}, your 'tactical' decisions are nothing more than a series of unfortunate events. The Oratrice rules in favor of {interaction.user.mention}!",
                    f"**CLOWN FIASCO!** {defendant.mention}, I’ve seen better positioning from a target dummy. Your presence on the Rift is a tragedy, and {interaction.user.mention} is the only hero here.",
                    f"**BEYOND REDEMPTION!** {defendant.mention}, you didn't just throw the game; you launched it into orbit! The court finds you guilty of high treason against the LP of {interaction.user.mention}.",
                    f"**CASE CLOSED!** {defendant.mention}, your inability to land a single skillshot has reached legendary levels of failure. {interaction.user.mention} is officially acquitted!"
                ]
                random.shuffle(self.guilty_deck)
            verdict = self.guilty_deck.pop(0)
            color = discord.Color.red()
        else:
            if not self.plot_twist_deck:
                self.plot_twist_deck = [
                    f"**PLOT TWIST!** {interaction.user.mention}, you dare accuse them when your own macro is this tragic? The Oratrice finds YOU guilty of throwing!",
                    f"**REVERSAL!** Upon further inspection, {interaction.user.mention} was the one running it down all along! {defendant.mention} is innocent!",
                    f"**FALSE ACCUSATION!** {interaction.user.mention}, attempting to deflect blame only highlights your own failures. The Oratrice sentences YOU!",
                    f"**THE AUDACITY!** {interaction.user.mention}, you brought this case to my court while your own KDA is a literal disaster? You are the one who is guilty!",
                    f"**REVERSAL OF FATE!** {interaction.user.mention}, you claim {defendant.mention} was the problem, yet you were the one hiding in the fountain during every team fight! GUILTY!",
                    f"**IRONY AT ITS FINEST!** {interaction.user.mention}, pointing fingers won't hide your 15% kill participation. The Oratrice finds YOU responsible for this theatrical disaster!",
                    f"**PERJURY!** {interaction.user.mention}, you attempted to frame {defendant.mention} for your own mechanical collapse. For this deception, the court sentences YOU to the bronze abyss!",
                    f"**THE FINAL BLUFF!** {interaction.user.mention}, did you think I wouldn't notice your damage chart? You dealt less than the support! The Oratrice finds the accuser guilty!"
                ]
                random.shuffle(self.plot_twist_deck)
            verdict = self.plot_twist_deck.pop(0)
            color = discord.Color.blue()

        # Deliver the final judgment
        embed = discord.Embed(title="📜 Final Verdict", description=verdict, color=color)
        await spinning_msg.edit(content=None, embed=embed)

    # The Confess command
    # What does it do? the victim can plead again
    @app_commands.command(name="confess", description="Admit your horrific misplays and beg the Oratrice for mercy.")
    @app_commands.describe(crime="What atrocious play did you commit?")
    async def confess(self, interaction: discord.Interaction, crime: str):
        await interaction.response.send_message(f"🙏 {interaction.user.mention} has approached the stand to confess: **\"{crime}\"**")

        await asyncio.sleep(3)
        msg = await interaction.followup.send("⚙️ *The Oratrice Mecanique d'Analyse Cardinale is evaluating your sincerity...*", wait=True)
        await asyncio.sleep(4)

        is_forgiven = random.choice([True, False])

        if is_forgiven:
            if not self.mercy_deck:
                self.mercy_deck = [
                    f"**FORGIVEN!** The Oratrice senses true remorse for your '{crime}'. Your LP will be spared.",
                    f"**ABSOLVED!** A momentary lapse in judgment like '{crime}' does not define a star.",
                    "**CLEANSED!** Your honesty is refreshing. I shall personally see to it that your next teammates have actual human souls.",
                    "**MERCY GRANTED!** Even the grandest stage has its blunders. You are free to return to the Rift, hopefully with more poise.",
                    "**EXCUSED!** The Oratrice finds your crime... understandable. Barely. Take your acquittal and leave before I change my mind.",
                    "**REPRIEVED!** Justice is not always cold. Today, you receive the blessing of the court. Do not waste it on a missed Smite.",
                    "**GRACE BESTOWED!** A rare display of humility. I find your confession sufficient to offset your tragic mechanical failure.",
                    "**NOT GUILTY!** While your play was an eyesore, your soul remains intact. The court dismisses these charges."
                ]
                random.shuffle(self.mercy_deck)
            verdict = self.mercy_deck.pop(0)
            color = discord.Color.green()
        else:
            if not self.sentence_deck:
                self.sentence_deck = [
                    "**UNFORGIVABLE!** A confession does not erase a tragedy! The Oratrice sentences you to 5 games of Loser's Queue.",
                    "**CONDEMNED!** You admit to such a crime and expect mercy? Your next 3 promos shall be populated entirely by inters!",
                    "**GUILTY!** Honesty is noble, but your gameplay was a crime against humanity. The court sentences you to the Bronze Abyss.",
                    "**NO MERCY!** I am a judge, not a saint! For that atrocious misplay, you shall suffer a 20-game winless streak.",
                    "**EXECUTION!** (Of your LP, that is). Your confession only highlights how truly horrific your macro has become!",
                    "**BANISHED!** Leave my sight! The Oratrice finds your sincerity lacking and your skillshots even worse.",
                    "**SENTENCED!** You shall be forced to play with a 0/10 Yasuo main for the remainder of the evening. Court adjourned!",
                    "**TRAGIC!** Your confession is as messy as your kiting. The Oratrice orders a permanent demotion to the depths of Iron."
                ]
                random.shuffle(self.sentence_deck)
            verdict = self.sentence_deck.pop(0)
            color = discord.Color.red()

        # Final reveal
        embed = discord.Embed(title="📜 Final Judgment", description=verdict, color=color)
        await msg.edit(content=None, embed=embed)

# Setup hook to load the Cog
async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))