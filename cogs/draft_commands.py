import discord
from discord.ext import commands
import asyncio
import re

# Initiate Riot ID Parser as a function.
# this is to prevent the user from formatting it wrong, for example they might type "Hide on bush KR1" instead of "Hide on bush#KR1".
def parse_riot_id(full_riot_id: str):
    if len(full_riot_id) > 22:  # 16 (name) + 1 (#) + 5 (tag)
        return None, None
    
    if '#' in full_riot_id:
        game_name, tag_line = full_riot_id.split('#', 1)
    else:
        parts = full_riot_id.rsplit(' ', 1)
        if len(parts) == 2:
            game_name, tag_line = parts[0], parts[1]
        else:
            return None, None # Returns None if they formatted it completely wrong

    return game_name.strip(), tag_line.strip()

# Initiate Winrate as a function
def parse_winrate(rank_string):
    if not rank_string or "Unranked" in rank_string:
        return 50.0 # If unranked or missing, assume an average 50% player

    # Searches for numbers directly followed by "% WR"
    match = re.search(r"(\d+)%\sWR", rank_string)
    if match:
        return float(match.group(1))
    return 50.0

# Initiate Role Sorter as a function.
def _assign_role_from_pool(roles, unassigned, role_idx, db_key, meta_db):
    if roles[role_idx] is not None:
        return
    pool = meta_db.get(db_key, set())
    for i, champ in enumerate(unassigned):
        if champ in pool:
            roles[role_idx] = champ
            unassigned.pop(i)
            return

# Sort Team Composition by role, not by pick
def sort_team_roles(team_participants, champ_dict, meta_db):
    roles = [None] * 5
    unassigned = []

    for player in team_participants:
        champ_name = champ_dict.get(str(player['championId']), "Unknown")
        if roles[1] is None and 11 in (player.get('spell1Id'), player.get('spell2Id')):
            roles[1] = champ_name
        else:
            unassigned.append(champ_name)

    # Use the new external helper instead of a nested function
    _assign_role_from_pool(roles, unassigned, 3, "PURE_ADCS", meta_db)
    _assign_role_from_pool(roles, unassigned, 4, "PURE_SUPPORTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 3, "FLEX_BOTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 4, "FLEX_SUPPORTS", meta_db)
    _assign_role_from_pool(roles, unassigned, 2, "KNOWN_MIDS", meta_db)
    _assign_role_from_pool(roles, unassigned, 0, "KNOWN_TOPS", meta_db)

    for i in range(5):
        if roles[i] is None and unassigned:
            roles[i] = unassigned.pop(0)

    if None in roles or unassigned:
        return [champ_dict.get(str(p['championId']), "Unknown") for p in team_participants]

    return roles

# Cog Class
class DraftCommands(commands.Cog):
    def __init__(self, bot, riot_client, ai_system, meta_db, champ_dict):
        # Store everything here to use for the bot commands yeah yessir.
        self.bot = bot
        self.riot = riot_client
        self.ai = ai_system
        self.meta_db = meta_db
        self.champ_dict = champ_dict

    # Initiate the ban logic as a function
    def _extract_bans(self, match_data):
        blue_bans, red_bans = ["None"] * 5, ["None"] * 5
        b_count, r_count = 0, 0
        for ban in match_data.get('bannedChampions', []):
            c_name = self.champ_dict.get(str(ban['championId']), "None")
            if ban['teamId'] == 100 and b_count < 5:
                blue_bans[b_count] = c_name
                b_count += 1
            elif ban['teamId'] == 200 and r_count < 5:
                red_bans[r_count] = c_name
                r_count += 1
        return blue_bans, red_bans

    # Initiate the checking logic as a function
    def _check_if_bot(self, champ_name, raw_team):
        for p in raw_team:
            if self.champ_dict.get(str(p['championId']), "Unknown") == champ_name:
                return p.get('bot', False) or not p.get('puuid')
        return False

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("I'm online!")

    @commands.command(name="help")
    async def custom_help(self, ctx):
        embed = discord.Embed(
            title="💧 Furina League Analyst Bot - Help Menu",
            description="I am Furina, your personal Solo Queue analyst! Here is how to use my commands:\n"
                        "Prefix: `f` or `furina` (e.g., `f ping`, `furina predict`)",
            color=discord.Color.blue()
        )
        embed.add_field(name="🏓 `f ping`", value="Checks if Furina is online.", inline=False)
        embed.add_field(name="⚔️ `f predict`", value="Calculates win probability. Format: `f predict Name#Tag`",inline=False)
        embed.add_field(name="🕵️ `f scout`", value="Builds an enemy dossier. Format: `f scout Name#Tag`", inline=False)
        await ctx.send(embed=embed)

    # Getting the Live game command.
    # Predict the win condition before the game starts
    @commands.command()
    async def predict(self, ctx, *, full_riot_id: str):
        # This call out the Riot ID parser
        game_name, tag_line = parse_riot_id(full_riot_id)
        if not game_name:
            await ctx.send("⚠️ Format Error! Please use: `f predict Name#Tag`")
            return

        await ctx.send(f"Fetching live match data for {game_name} #{tag_line}...")

        try:
            # This call out get_puuid function from RiotAPIClient Class in riot_api.py.
            puuid = await self.riot.get_puuid(game_name, tag_line)
            if not puuid:
                await ctx.send(f"⚠️ Could not find player {game_name} #{tag_line}. Check spelling!")
                return

            # This call out get_live_match function from RiotAPIClient Class in riot_api.py.
            match_data = await self.riot.get_live_match(puuid)
            if not match_data:
                await ctx.send("⚠️ This player is not currently in a live match!")
                return

            # Sort the teams
            raw_blue_team = [p for p in match_data['participants'] if p['teamId'] == 100]
            raw_red_team = [p for p in match_data['participants'] if p['teamId'] == 200]

            blue_picks = sort_team_roles(raw_blue_team, self.champ_dict, self.meta_db)
            red_picks = sort_team_roles(raw_red_team, self.champ_dict, self.meta_db)

            if len(blue_picks) < 5 or len(red_picks) < 5:
                await ctx.send("⚠️ **Not enough players!** I only calculate full 5v5 matches.")
                return

            # Get _check_if_bot function
            blue_display = [f"🤖 {c}" if self._check_if_bot(c, raw_blue_team) else c for c in blue_picks]
            red_display = [f"🤖 {c}" if self._check_if_bot(c, raw_red_team) else c for c in red_picks]

            # Basically Get the Champion picks and then set them in order.
            draft_dict = {
                'blueTopChamp': blue_picks[0], 'blueJungleChamp': blue_picks[1], 'blueMiddleChamp': blue_picks[2],
                'blueADCChamp': blue_picks[3], 'blueSupportChamp': blue_picks[4],
                'redTopChamp': red_picks[0], 'redJungleChamp': red_picks[1], 'redMiddleChamp': red_picks[2],
                'redADCChamp': red_picks[3], 'redSupportChamp': red_picks[4]
            }

            # Calculates the probability
            base_blue_prob,_, blue_syn, red_syn = self.ai.predict_match(draft_dict)

            blue_sum_ids = [p['summonerId'] for p in raw_blue_team if p.get('summonerId')]
            red_sum_ids = [p['summonerId'] for p in raw_red_team if p.get('summonerId')]

            # Create the 10 concurrent tasks
            blue_tasks = [self.riot.get_summoner_rank(sid) for sid in blue_sum_ids]
            red_tasks = [self.riot.get_summoner_rank(sid) for sid in red_sum_ids]

            # This prevents the 15-second hang
            blue_results = await asyncio.gather(*blue_tasks)
            red_results = await asyncio.gather(*red_tasks)

            # The hybrid algorithm
            blue_winrates = [parse_winrate(res) for res in blue_results]
            red_winrates = [parse_winrate(res) for res in red_results]

            avg_blue_wr = sum(blue_winrates) / len(blue_winrates) if blue_winrates else 50.0
            avg_red_wr = sum(red_winrates) / len(red_winrates) if red_winrates else 50.0

            final_blue_prob, final_red_prob = self.ai.apply_hybrid_algorithm(base_blue_prob, blue_winrates,red_winrates)

            # Send the results to the discord, design doesn't matter at least lol.
            embed = discord.Embed(title="🔴 LIVE MATCH PREDICTION", color=discord.Color.blue())
            blue_text = (
                    f"**Win Chance: {final_blue_prob * 100:.1f}%**\n"
                    f"*(Avg WR: {avg_blue_wr:.1f}%)*\n"
                    f"*(Synergy: {blue_syn * 100:+.1f})*\n\n"
                    f"**Draft:**\n" + "\n".join(blue_display)
            )

            red_text = (
                    f"**Win Chance: {final_red_prob * 100:.1f}%**\n"
                    f"*(Avg WR: {avg_red_wr:.1f}%)*\n"
                    f"*(Synergy: {red_syn * 100:+.1f})*\n\n"
                    f"**Draft:**\n" + "\n".join(red_display)
            )

            embed.add_field(name="🟦 Blue Team", value=blue_text, inline=True)
            embed.add_field(name="🟥 Red Team", value=red_text, inline=True)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"⚠️ An unexpected error occurred: {str(e)}")

    # Initiate Dossier Builder as a function
    async def _build_enemy_dossier(self, match_data, enemy_team_id, embed):
        for p in match_data['participants']:
            if p['teamId'] == enemy_team_id:
                e_puuid = p.get('puuid')
                riot_id = p.get('riotIdGlobalName') or p.get('summonerName') or 'Unknown Player'
                c_id = p['championId']
                c_name = self.champ_dict.get(str(c_id), 'Unknown')

                if p.get('bot', False) or not e_puuid:
                    embed.add_field(name=f"🤖 {c_name} (Bot)", value="No data available.", inline=False)
                    continue

                mastery = await self.riot.get_champion_mastery(e_puuid, c_id)
                sum_id = p.get('summonerId') or await self.riot.get_summoner_id(e_puuid)
                rank = await self.riot.get_summoner_rank(sum_id) if sum_id else "Unranked"

                embed.add_field(name=f"⚔️ {c_name} - {riot_id}",
                                value=f"**Rank:** {rank}\n**Mastery:** {mastery:,} pts", inline=False)
        return embed

    # This part checks what type of bs the enemy team is running
    @commands.command()
    async def scout(self, ctx, *, full_riot_id: str):
        # This call out the Riot ID parser
        game_name, tag_line = parse_riot_id(full_riot_id)

        # Same as above bouncer, yeah yeah yeah.
        if not game_name:
            await ctx.send("⚠️ Format Error! Please use: `f scout Name#Tag` or `f scout Name Tag`")
            return

        await ctx.send(f"🕵️ Scouting the enemy team for {game_name} #{tag_line}...")

        try:
            # This call out get_riot_puuid function from RiotAPIClient Class in riot_api.py.
            puuid = await self.riot.get_puuid(game_name, tag_line)
            if not puuid:
                await ctx.send(f"⚠️ Could not find player {game_name} #{tag_line}. Check spelling!")
                return

            # This call out get_live_match function from RiotAPIClient Class in riot_api.py.
            match_data = await self.riot.get_live_match(puuid)
            if not match_data:
                await ctx.send("⚠️ This player is not currently in a live match!")
                return

            # Figures which team the current user is on Blue or Red.
            user_team = next((p['teamId'] for p in match_data['participants'] if p['puuid'] == puuid), None)
            if not user_team:
                await ctx.send("⚠️ Could not locate user in match data.")
                return

            enemy_team_id = 200 if user_team == 100 else 100

            # Building the Discord Embed
            embed = discord.Embed(title="🕵️ Enemy Team Dossier", description=f"Scouting for **{game_name}**", color=discord.Color.dark_purple())

            # Get _build_enemy_dossier
            embed = await self._build_enemy_dossier(match_data, enemy_team_id, embed)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"⚠️ An unexpected error occurred: {str(e)}")

# Setup Hook or something whatever this is called.
async def setup(bot):
    await bot.add_cog(DraftCommands(bot, bot.riot_client, bot.ai_system, bot.meta_db, bot.champ_dict))