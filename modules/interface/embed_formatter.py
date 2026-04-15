"""
This handle embed formatting for the commands.
It takes in the relevant data and constructs a Discord Embed object with the appropriate structure and styling for each command's output.
"""

import discord
from modules.utils.parsers import ParsedStats
from modules.persona.tags import get_pregame_tags, get_performance_tags, get_draft_warnings
from modules.persona.verdicts import generate_furina_verdict
from modules.utils.data_loader import ITEM_DB, RUNE_DB, SPELL_DB
from config import QUEUE_MAP
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
    # System Command
    embed.add_field(name="🏓 `/ping`",value="Checks my current latency to Discord.",inline=False)

    # The Court and Hall of Shame
    embed.add_field(name="🔗 `/link`", value="Link your Riot ID to the Oratrice for Hall of Shame tracking.\n**Requires:** Server and Riot ID", inline=False)
    embed.add_field(name="✂️ `/unlink`", value="Sever your ties and Furina will wipe your records clean.", inline=False)
    embed.add_field(name="🏛️ `/hallofshame`", value="View the server's most tragic League of Legends performers this week.", inline=False)
    embed.add_field(name="⚖️ `/trial`", value="Judge who truly threw the game and deliver a final verdict.", inline=False)
    embed.add_field(name="🗣 `/confess`", value="Admit your horrific misplays and beg the Oratrice for mercy.", inline=False)

    # Game Analysis
    embed.add_field(name="⚔️ `/predict`",value="Calculates win probability for a live match.\n**Requires:** Server and Riot ID",inline=False)
    embed.add_field(name="🕵️ `/scout`",value="Builds an enemy dossier for a live match.\n**Requires:** Server and Riot ID", inline=False)
    embed.add_field(name="🏆 `/postgame`",value="Ruthlessly analyzes your most recent match, including lane rival diff and performance grades.\n**Requires:** Server and Riot ID",inline=False)
    embed.add_field(name="🧠 `/coach`", value="Simulates optimal champion picks for your specific role and team side during the draft phase.", inline=False)

    # Live Match
    embed.add_field(name="👑 Admin Configuration", value="**`/setup_broadcast`** — Automatically builds the `#live-matches` infrastructure so the Oratrice can track and announce linked players entering live games.", inline=False)

    # Footer
    embed.set_footer(text="Valid servers: NA1, EUW1, EUN1, KR, SG2, TW2, VN2, TH2, PH2, BR1, LAN1, LAS1, OC1, TR1, RU")

    return embed

# For predict commands in cogs
def build_predict_embed(blue_prob: float, red_prob: float, avg_blue_wr: float, avg_red_wr: float, blue_synergy: float, red_synergy: float, match_data: dict) -> discord.Embed:
    queue_id = match_data.get('gameQueueConfigId')
    game_mode = QUEUE_MAP.get(queue_id) or QUEUE_MAP.get(str(queue_id)) or match_data.get('gameMode', 'Unknown Mode')
    match_id = match_data.get('gameId', 'Unknown ID')

    if blue_prob > red_prob:
        color = discord.Color.blue()
        adv = blue_prob - red_prob
        verdict = "🥇 **Blue Team is heavily favored to win.**" if adv > 0.15 else "🥈 **Blue Team has a slight draft advantage.**"
    else:
        color = discord.Color.red()
        adv = red_prob - blue_prob
        verdict = "🥇 **Red Team is heavily favored to win.**" if adv > 0.15 else "🥈 **Red Team has a slight draft advantage.**"

    description = (
        f"{verdict}\n\n"
        f"**📊 Roster Analytics:**\n"
        f"> 🟦 **Blue Team**\n"
        f"> └ Avg WR: `{avg_blue_wr:.1f}%`  |  Synergy: `{blue_synergy * 100:+.1f}`\n"
        f"> \n"
        f"> 🟥 **Red Team**\n"
        f"> └ Avg WR: `{avg_red_wr:.1f}%`  |  Synergy: `{red_synergy * 100:+.1f}`"
    )

    embed = discord.Embed(
        title="🔴 LIVE MATCH ANALYSIS",
        description=description,
        color=color
    )

    embed.set_image(url="attachment://draft_board.png")
    embed.set_footer(text=f"Mode: {game_mode} | Match ID: {match_id}")

    return embed

# For scout command in cogs
def build_scout_embed(server: str, game_name: str, bots: list, players: list, meta_db: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"🕵️ ENEMY DOSSIER: {server.upper()}",
        description=f"Live Threat Assessment for **{game_name}**\n" + "▬" * 30,
        color=discord.Color.dark_red()
    )

    for c_name in bots:
        embed.add_field(name=f"🤖 {c_name} (Bot)", value="> No data available for AI.", inline=False)

    for c_name, riot_id, rank, mastery, is_duo, keystone, is_otp, is_autofilled in players:
        meta_wr = meta_db.get(c_name, 0.50)
        tag_string = get_pregame_tags(mastery, is_otp, is_duo, is_autofilled, meta_wr, rank)

        # Tags and Keystone
        tag_display = f"\n> 🏷️ **Tags:** {tag_string}" if tag_string else ""
        keystone_display = keystone if keystone != "None" else "Unknown"

        #  Strip the 'Flex' prefix
        if "\n" in rank:
            # Re-indent the second line so it perfectly aligns with the top line
            rank = rank.replace("\nFlex:", "\n> 🏅 **Flex:**").replace("\n**Flex:**", "\n> 🏅 **Flex:**")
        elif rank.startswith("Flex "):
            # Handle players who ONLY have a Flex rank
            rank = rank.replace("Flex ", "", 1)
            if " |" in rank:
                rank = rank.replace(" |", " *(Flex)* |", 1)
            else:
                rank += " *(Flex)*"

        # OP.GG uses dashes instead of hashtags, and we grab the first 2 letters of the server (e.g., 'na1' -> 'na')
        safe_id = riot_id.replace('#', '-').replace(' ', '%20')
        opgg_url = f"https://www.op.gg/summoners/{server[:2].lower()}/{safe_id}"

        value = (
            f"> 🏅 **Rank:** {rank}  |  [🔗 OP.GG]({opgg_url})\n"
            f"> 🔮 **Rune:** {keystone_display}\n"
            f"> 🗡️ **Mastery:** {mastery:,} pts{tag_display}"
        )

        embed.add_field(
            name=f"⚔️ {c_name}  •  {riot_id}",
            value=value,
            inline=False
        )

    return embed

# For last game command in cogs
def build_lastgame_embed(server: str, riot_id: str, stats: dict, patch_version: str) -> discord.Embed:
    p = ParsedStats(stats)
    color = discord.Color.green() if p.win else discord.Color.red()
    title = f"{'🏆 VICTORY' if p.win else '💀 DEFEAT'}: {riot_id} on {server.upper()}"

    embed = discord.Embed(title=title, color=color)

    # Convert seconds to MM:SS format
    minutes, seconds = divmod(p.time, 60)
    duration_str = f"{minutes}:{seconds:02d}"

    # The Verdict
    verdict_text = generate_furina_verdict(stats)

    # Top level description
    embed.description = (
        f"⚖️ **FURINA'S FINAL JUDGMENT**\n"
        f"*\"{verdict_text}\"*\n\n"
        f"**Match ID:** `{p.match_id}`  |  **Duration:** `{duration_str}`\n"
        f"{'▬' * 28}"
    )

    # Calculate Lane Rival Diffs
    dmg_diff_str = "N/A"
    gold_diff_str = "N/A"
    rival_display = "Unknown"

    if p.rival and p.role not in ["", "Invalid"]:
        rival_display = p.rival.get('championName', 'Unknown')
        dmg_diff = p.damage - p.rival.get('totalDamageDealtToChampions', 0)
        gold_diff = p.gold - p.rival.get('goldEarned', 0)

        # Format with plus signs and commas
        dmg_diff_str = f"{'+' if dmg_diff > 0 else ''}{dmg_diff:,}"
        gold_diff_str = f"{'+' if gold_diff > 0 else ''}{gold_diff:,}"

    # Build the Terminal Tree for Performance
    performance_text = (
        f"> ⚔️ **Matchup:** `{p.champ}` vs `{rival_display}`\n"
        f"> └ DMG Diff: `{dmg_diff_str}`  |  Gold Diff: `{gold_diff_str}`\n"
        f"> \n"
        f"> 📊 **Combat Data:**\n"
        f"> └ KDA: `{p.kills}/{p.deaths}/{p.assists}` (`{p.kp_percent:.1f}%` KP)\n"
        f"> └ CS/Min: `{p.cs_per_min:.1f}`  |  Vision: `{p.vision_score}`\n"
        f"> \n"
        f"> 🏅 **Final Grade:** `{p.get_grade()}`"
    )

    embed.add_field(name="🎯 Match Performance", value=performance_text, inline=False)

    keystone = RUNE_DB.get(str(p.keystone_id), "None")
    spell1 = SPELL_DB.get(str(p.spell1_id), "Unknown")
    spell2 = SPELL_DB.get(str(p.spell2_id), "Unknown")
    items = [ITEM_DB.get(str(i), 'Unknown') for i in p.items if i != 0]
    build_string = " • ".join(items) if items else "Empty"

    loadout_text = (
        f"> 🔮 **Runes & Spells:**\n"
        f"> └ `{keystone}`  |  `{spell1}` & `{spell2}`\n"
        f"> \n"
        f"> 🎒 **Final Build:**\n"
        f"> └ {build_string}"
    )

    embed.add_field(name="⚙️ Equipment", value=loadout_text, inline=False)

    # Performance Tags & Verdict
    if perf_tags := get_performance_tags(stats):
        embed.add_field(name="🏷️ Match Tags", value=perf_tags, inline=False)

    # Visuals
    safe_champ = p.champ.replace(" ", "").replace("'", "").title()
    embed.set_thumbnail(url=f"https://ddragon.leagueoflegends.com/cdn/{patch_version}/img/champion/{safe_champ}.png")

    # Footer
    embed.set_footer(text=f"\n\nMode: {p.game_mode}")

    return embed

# For the draft coach command
def build_draft_embed(role: str, user_team: str, error_msg: str | None, top_picks: list, blue_dict: dict, red_dict: dict, role_db: dict) -> discord.Embed:
    desc = f"Simulating optimal **{role.title()}** picks for the **{user_team}** side."
    if error_msg:
        desc = f"🚨 **ERROR: {error_msg}**\n\n" + desc

    # Team Composition Warnings
    current_draft = blue_dict.values() if user_team == "Blue" else red_dict.values()
    locked_champs = [c for c in current_draft if c != "Unknown"]

    if warnings := get_draft_warnings(locked_champs, role_db):
        desc += "\n\n" + "\n".join(warnings)

    # Embed Color
    embed_color = discord.Color.red() if error_msg or user_team != "Blue" else discord.Color.blue()

    embed = discord.Embed(
        title="🧠 Furina's Live Draft Coach",
        description=desc,
        color=embed_color
    )

    # Predictions
    if not top_picks:
        embed.add_field(name="⚠️ Standby", value="Waiting for more data to simulate...", inline=False)
    else:
        for rank, data in enumerate(top_picks, 1):
            # Safe unpacking in case an older tuple is passed
            if len(data) == 3:
                champ, prob, reason = data
                embed.add_field(name=f"#{rank} - {champ}", value=f"Predicted WR: **{prob * 100:.1f}%**\n💡 *{reason}*", inline=False)
            else:
                champ, prob = data
                embed.add_field(name=f"#{rank} - {champ}", value=f"Predicted WR: **{prob * 100:.1f}%**", inline=False)

    embed.set_image(url="attachment://draft_board.png")

    return embed