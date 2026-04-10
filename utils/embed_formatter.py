"""
This handle embed formatting for the commands.
It takes in the relevant data and constructs a Discord Embed object with the appropriate structure and styling for each command's output.
"""

import discord
import random
from typing import List, Tuple
from utils.roasts import RoastGenerator
from utils.tags import get_pregame_tags, get_performance_tags


# Helper functions
# Verdicts for post game review
def _generate_furina_verdict(stats: dict) -> str:
    # Initialize the Roast Engine
    engine = RoastGenerator(stats)

    # Collect all matches instead of stopping at the first one
    applied_roasts = []
    for condition, verdict in engine.get_all_rules():
        if condition():
            applied_roasts.append(verdict)

    # Fallback just in case the player is so average, imagine being so average.
    if not applied_roasts:
        win = stats.get('win', False)

        fallback_wins = [
            "A perfectly acceptable victory. Nothing more, nothing less.",
            "You won. The crowd goes mild.",
            "A victory so utterly standard it defies any attempt at commentary.",
            "You secured the win without doing anything remarkably stupid or remarkably brilliant. How quaint.",
            "The Nexus exploded in your favor, yet I am left entirely uninspired by how it happened."
        ]

        fallback_losses = [
            "A rather embarrassing defeat. Please, try to be more entertaining next time.",
            "You lost. It was neither a spectacular tragedy nor a close match. It was simply a waste of time.",
            "Defeat. The most interesting thing about this match is that it eventually ended.",
            "You played, you lost, and the world continues to spin completely unchanged.",
            "A flawlessly generic defeat. You didn't even fail spectacularly enough to warrant a proper roast."
        ]

        return random.choice(fallback_wins) if win else random.choice(fallback_losses)

    # (The [:1024] protects the bot from crashing Discord's embed character limit)
    combo_roast = " ".join(applied_roasts)
    if len(combo_roast) > 1024:
        suffixes = [
            "... And so much more. Truly a performance for the ages.",
            "... The list goes on, but I am simply too exhausted to continue.",
            "... I could keep going, but frankly, you are not worth my breath.",
            "... A tragedy so long, Discord physically will not let me finish it.",
            "... And that is only half of it. Please, log off and reflect on your choices.",
            "... I have run out of breath. Just uninstall the game.",
            "... I would list the rest of your blunders, but the audience is already leaving. What an absolute farce.",
            "... The Oratrice Mecanique d'Analyse Cardinale has quite literally overheated trying to process the sheer volume of your crimes. I rest my case.",
            "... To recount the entirety of this tragedy would take a full theatrical season. Let us just draw the curtains and pretend this never happened."
        ]

        # Choose a random suffix to add some variety to the bot's responses when the roast is too long
        chose_suffix = random.choice(suffixes)

        # Calculate how many characters we have left for the roast after adding the suffix
        safe_cut = 1020 - len(chose_suffix)
        raw_cut = combo_roast[:safe_cut]

        # Walk backward to the last space so we don't chop a word in half!
        clean_cut = raw_cut.rsplit(' ', 1)[0]

        return clean_cut + chose_suffix

    return combo_roast

# The embed formatter sections
# For help commands in cogs
def build_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💧 Furina League Analyst Bot - Help Menu",
        description="I am Furina, your personal Solo Queue analyst! I now use **Slash Commands**:\n"
                    "Just type `/` and select my commands from the menu!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🏓 `/ping`",
        value="Checks my current latency to Discord.",
        inline=False
    )
    embed.add_field(
        name="⚔️ `/predict`",
        value="Calculates win probability for a live match.\n"
              "**Requires:** Server and Riot ID",
        inline=False
    )
    embed.add_field(
        name="🕵️ `/scout`",
        value="Builds an enemy dossier for a live match.\n"
              "**Requires:** Server and Riot ID",
        inline=False
    )
    embed.set_footer(
        text="Valid servers: NA1, EUW1, EUN1, KR, SG2, TW2, VN2, TH2, PH2, BR1, LAN1, LAS1, OC1, TR1, RU"
    )

    return embed

# For predict commands in cogs
def build_predict_embeds(blue_prob: float, red_prob: float,
                         avg_blue_wr: float, avg_red_wr: float,
                         blue_synergy: float, red_synergy: float,
                         blue_display: List[str], red_display: List[str]) -> Tuple[discord.Embed, discord.Embed]:

    description = f"**Blue Win Chance:** {blue_prob * 100:.1f}%\n**Red Win Chance:** {red_prob * 100:.1f}%"

    # Blue
    blue_embed = discord.Embed(title="🔴 LIVE MATCH PREDICTION", description=description, color=discord.Color.blue())
    blue_text = (
            f"*(Avg WR: {avg_blue_wr:.1f}%)*\n"
            f"*(Synergy: {blue_synergy * 100:+.1f})*\n\n"
            f"**Draft:**\n" + "\n".join(blue_display)
    )
    blue_embed.add_field(name="🟦 Blue Team Data", value=blue_text, inline=False)

    # Red
    red_embed = discord.Embed(title="🔴 LIVE MATCH PREDICTION", description=description, color=discord.Color.red())
    red_text = (
            f"*(Avg WR: {avg_red_wr:.1f}%)*\n"
            f"*(Synergy: {red_synergy * 100:+.1f})*\n\n"
            f"**Draft:**\n" + "\n".join(red_display)
    )
    red_embed.add_field(name="🟥 Red Team Data", value=red_text, inline=False)

    return blue_embed, red_embed

# For scout command in cogs
def build_scout_embed(server: str, game_name: str, bots: list, players: list, meta_db: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"🕵️ Enemy Team Dossier ({server.upper()})",
        description=f"Scouting for **{game_name}**",
        color=discord.Color.dark_purple()
    )

    for c_name in bots:
        embed.add_field(name=f"🤖 {c_name} (Bot)", value="No data available.", inline=False)

    for c_name, riot_id, rank, mastery, is_duo, keystone, is_otp, is_autofilled in players:
        meta_wr = meta_db.get(c_name, 0.50)
        tag_string = get_pregame_tags(mastery, is_otp, is_duo, is_autofilled, meta_wr, rank)
        tag_display = f"\n**Tags:** {tag_string}" if tag_string else ""

        keystone_display = f" [{keystone}]" if keystone != "None" else ""

        embed.add_field(
            name=f"⚔️ {c_name}{keystone_display} - {riot_id}",
            value=f"**Rank:** {rank}\n**Mastery:** {mastery:,} pts{tag_display}",
            inline=False
        )

    return embed

# For last game command in cogs
def build_lastgame_embed(server: str, riot_id: str, stats: dict, patch_version: str) -> discord.Embed:
    win = stats.get('win', False)
    color = discord.Color.green() if win else discord.Color.red()
    title = "🏆 VICTORY" if win else "💀 DEFEAT"

    # Get the stats and calculate
    champ = stats.get('championName', 'Unknown')
    kda = f"{stats.get('kills')}/{stats.get('deaths')}/{stats.get('assists')}"
    cs = stats.get('totalMinionsKilled', 0) + stats.get('neutralMinionsKilled', 0)
    damage = stats.get('totalDamageDealtToChampions', 0)
    gold = stats.get('goldEarned', 0)
    game_mode = stats.get('gameMode', 'UNKNOWN MODE')
    match_id = stats.get('matchId', 'UNKNOWN_ID')
    vision = stats.get('visionScore', 0)
    pink_wards = stats.get('visionWardsBoughtInGame', 0)
    team_kills = stats.get('teamKills', 1)  # Fallback to 1 to prevent division by zero
    kp_percent = ((stats.get('kills', 0) + stats.get('assists', 0)) / team_kills) * 100 if team_kills > 0 else 0
    minutes = stats.get('gameDuration', 1) / 60.0
    cs_per_min = cs / minutes if minutes > 0 else 0
    perf_tags = get_performance_tags(stats)

    # Get Furina's verdict about the player's performance based on the stats
    verdict = _generate_furina_verdict(stats)

    # Header
    embed = discord.Embed(title=f"{title}: {riot_id} on {server.upper()}", color=color)

    embed.add_field(name="👤 Champion", value=f"**{champ}**", inline=True)
    embed.add_field(name="⚔️ KDA", value=f"**{kda}**\n({kp_percent:.0f}% KP)", inline=True)
    embed.add_field(name="💥 Damage", value=f"**{damage:,}** DMG", inline=True)

    embed.add_field(name="🌾 Farming", value=f"**{cs} CS**\n({cs_per_min:.1f}/min)", inline=True)
    embed.add_field(name="💰 Gold", value=f"**{gold:,}** G", inline=True)
    embed.add_field(name="👁️ Vision", value=f"**{vision}** Score\n**{pink_wards}** Pinks", inline=True)

    if perf_tags:
        # If they earned tags, display them across the bottom!
        embed.add_field(name="🏷️ Match Tags", value=perf_tags, inline=False)

    # one blank row above the verdict
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    # Footer
    embed.add_field(name="⚖️ Furina's Verdict", value=f"*{verdict}*", inline=False)
    embed.set_footer(text=f"Mode: {game_mode} | Match ID: {match_id}")

    # Clean the champion's name
    safe_champ_name = champ.replace(" ", "").replace("'", "").title()

    # Set the thumbnail
    embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{patch_version}/img/champion/{safe_champ_name}.png")

    return embed