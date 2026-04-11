"""
This handle embed formatting for the commands.
It takes in the relevant data and constructs a Discord Embed object with the appropriate structure and styling for each command's output.
"""

import discord
from typing import List, Tuple
from utils.roasts import ParsedStats
from utils.tags import get_pregame_tags, get_performance_tags
from utils.verdicts import generate_furina_verdict
from utils.data_loader import ITEM_DB, RUNE_DB, SPELL_DB
import logging

# Get the logging system
logger = logging.getLogger(__name__)

# The embed formatter sections
# For help commands in cogs
def build_help_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💧 Furina League Analyst Bot - Help Menu",
        description="I am Furina, your personal Solo Queue analyst! I now use **Slash Commands**:\n"
                    "Just type `/` and select my commands from the menu!",
        color=discord.Color.blue()
    )
    embed.add_field(name="🏓 `/ping`",value="Checks my current latency to Discord.",inline=False)
    embed.add_field(name="⚔️ `/predict`",value="Calculates win probability for a live match.\n**Requires:** Server and Riot ID",inline=False)
    embed.add_field(name="🕵️ `/scout`",value="Builds an enemy dossier for a live match.\n**Requires:** Server and Riot ID", inline=False)
    embed.add_field(name="🏆 `/postgame`",value="Ruthlessly analyzes your most recent match, including lane rival diff and performance grades.\n**Requires:** Server and Riot ID",inline=False)
    embed.set_footer(text="Valid servers: NA1, EUW1, EUN1, KR, SG2, TW2, VN2, TH2, PH2, BR1, LAN1, LAS1, OC1, TR1, RU")

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
    p = ParsedStats(stats)
    color = discord.Color.green() if p.win else discord.Color.red()
    title = f"{'🏆 VICTORY' if p.win else '💀 DEFEAT'}: {riot_id} on {server.upper()}"

    embed = discord.Embed(title=title, color=color)

    # Helper to add fields quickly
    def add_row(fields):
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=True)

    # Grid Rows
    add_row([
        ("👤 Champion", f"**{p.champ}**\nGrade: **{p.get_grade()}**"),
        ("⚔️ KDA", f"**{p.kills}/{p.deaths}/{p.assists}**\n({p.kp_percent:.0f}% KP)"),
        ("💥 Damage", f"**{p.damage:,}** DMG")
    ])

    add_row([
        ("🌾 Farming", f"**{p.cs} CS**\n({p.cs_per_min:.1f}/min)"),
        ("💰 Gold", f"**{p.gold:,}** G"),
        ("👁️ Vision", f"**{p.vision_score}** Score\n**{p.vision_wards}** Pinks")
    ])

    if p.rival and p.role not in ["", "Invalid"]:
        dmg_diff = p.damage - p.rival.get('totalDamageDealtToChampions', 0)
        gold_diff = p.gold - p.rival.get('goldEarned', 0)
        add_row([
            (f"🆚 {p.role.capitalize()} Rival", f"**{p.rival.get('championName', 'Unknown')}**"),
            ("💥 DMG Diff", f"**{'📈' if dmg_diff > 0 else '📉'} {dmg_diff:+,}**"),
            ("🪙 Gold Diff", f"**{'📈' if gold_diff > 0 else '📉'} {gold_diff:+,}**")
        ])

    add_row([
        ("🔮 Keystone", RUNE_DB.get(str(p.keystone_id), "None")),
        ("🏮 Trinket", ITEM_DB.get(str(p.trinket), "None")),
        ("✨ Spells", f"{SPELL_DB.get(str(p.spell1_id), 'Unknown')} & {SPELL_DB.get(str(p.spell2_id), 'Unknown')}")
    ])

    # Items
    items = [ITEM_DB.get(str(i), 'Unknown') for i in p.items if i != 0]
    if len(items) > 3:
        row1 = " • ".join(items[:3])
        row2 = " • ".join(items[3:])
        build_string = f"{row1}\n{row2}"
    else:
        build_string = " • ".join(items) if items else "Empty"
    embed.add_field(name="🎒 Final Build", value=build_string, inline=False)

    # Performance Tags
    if perf_tags := get_performance_tags(stats):
        embed.add_field(name="🏷️ Match Tags", value=perf_tags, inline=False)

    # Verdict
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.add_field(name="⚖️ Furina's Verdict", value=f"*{generate_furina_verdict(stats)}*", inline=False)

    safe_champ = p.champ.replace(" ", "").replace("'", "").title()
    embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{patch_version}/img/champion/{safe_champ}.png")

    # Footer
    embed.set_footer(text=f"Mode: {p.game_mode} | Match ID: {p.match_id}")

    return embed