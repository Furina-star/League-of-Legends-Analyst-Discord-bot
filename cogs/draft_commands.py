import discord
from discord.ext import commands

# Initiate Riot ID Parser as a function.
# this is to prevent the user from formatting it wrong, for example they might type "Hide on bush KR1" instead of "Hide on bush#KR1".
def parse_riot_id(full_riot_id: str):
    if '#' in full_riot_id:
        game_name, tag_line = full_riot_id.split('#', 1)
    else:
        parts = full_riot_id.rsplit(' ', 1)
        if len(parts) == 2:
            game_name, tag_line = parts[0], parts[1]
        else:
            return None, None # Returns None if they formatted it completely wrong

    return game_name.strip(), tag_line.strip()

# Initiate Role Sorter as a function.
# Sort Team Composition by role, not by pick
def sort_team_roles(team_participants, champ_dict, meta_db):
    roles = [None, None, None, None, None]  # [Top, Jungle, Mid, ADC, Support]
    pool = []

    # The Jungler
    for player in team_participants:
        champ_name = champ_dict.get(str(player['championId']), "Unknown")
        spell1 = player.get('spell1Id')
        spell2 = player.get('spell2Id')

        if (spell1 == 11 or spell2 == 11) and roles[1] is None:
            roles[1] = champ_name
        else:
            pool.append(champ_name)

    # Pure Bots
    rem_pass2 = []
    for champ in pool:
        if champ in meta_db.get("PURE_ADCS", []) and roles[3] is None:
            roles[3] = champ
        elif champ in meta_db.get("PURE_SUPPORTS", []) and roles[4] is None:
            roles[4] = champ
        else:
            rem_pass2.append(champ)

    # Flex Bots
    rem_pass3 = []
    for champ in rem_pass2:
        if champ in meta_db.get("FLEX_BOTS", []) and roles[3] is None:
            roles[3] = champ
        elif champ in meta_db.get("FLEX_SUPPORTS", []) and roles[4] is None:
            roles[4] = champ
        else:
            rem_pass3.append(champ)

    # Solo Lanes
    rem_pass4 = []
    for champ in rem_pass3:
        if champ in meta_db.get("KNOWN_MIDS", []) and roles[2] is None:
            roles[2] = champ
        elif champ in meta_db.get("KNOWN_TOPS", []) and roles[0] is None:
            roles[0] = champ
        else:
            rem_pass4.append(champ)

    # Leftover Dump
    for i in range(5):
        if roles[i] is None and rem_pass4:
            roles[i] = rem_pass4.pop(0)

    if len(rem_pass4) > 0 or None in roles:
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

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("I'm online nigga!")

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

            # Check if there's a ducking bot everywhere like why???
            def check_if_bot(champ_name, raw_team):
                for p in raw_team:
                    if self.champ_dict.get(str(p['championId']), "Unknown") == champ_name:
                        return p.get('bot', False) or not p.get('puuid')
                return False

            blue_display = [f"🤖 {c}" if check_if_bot(c, raw_blue_team) else c for c in blue_picks]
            red_display = [f"🤖 {c}" if check_if_bot(c, raw_red_team) else c for c in red_picks]

            # This code snippet just basically re adjust the indexes especially when doing blind picks (SwiftPlay).
            blue_bans, red_bans = ["None"] * 5, ["None"] * 5
            blue_ban_count, red_ban_count = 0, 0

            # .get() prevents a crash if the game is Blind Pick (SwiftPlay) and has NO bans, it will just return an empty list and skip the loop.
            for ban in match_data.get('bannedChampions', []):
                # Default to "None" if the ID is missing or -1
                c_name = self.champ_dict.get(str(ban['championId']), "None")

                if ban['teamId'] == 100 and blue_ban_count < 5:
                    blue_bans[blue_ban_count] = c_name
                    blue_ban_count += 1
                elif ban['teamId'] == 200 and red_ban_count < 5:
                    red_bans[red_ban_count] = c_name
                    red_ban_count += 1

            # Basically Get the Champion picks and then set them in order.
            draft_dict = {
                'blueTopChamp': blue_picks[0], 'blueJungleChamp': blue_picks[1], 'blueMiddleChamp': blue_picks[2],
                'blueADCChamp': blue_picks[3], 'blueSupportChamp': blue_picks[4],
                'blueBan1': blue_bans[0], 'blueBan2': blue_bans[1], 'blueBan3': blue_bans[2], 'blueBan4': blue_bans[3],
                'blueBan5': blue_bans[4],
                'redTopChamp': red_picks[0], 'redJungleChamp': red_picks[1], 'redMiddleChamp': red_picks[2],
                'redADCChamp': red_picks[3], 'redSupportChamp': red_picks[4],
                'redBan1': red_bans[0], 'redBan2': red_bans[1], 'redBan3': red_bans[2], 'redBan4': red_bans[3],
                'redBan5': red_bans[4]
            }

            try:
                blue_win_prob, red_win_prob = self.ai.predict_match(draft_dict)
            except Exception as e:
                await ctx.send(f"⚠️ AI Calculation Error: {str(e)}")
                return

            # Send the results to the discord, design doesn't matter at least lol.
            embed = discord.Embed(title="🔴 LIVE MATCH PREDICTION", color=discord.Color.blue())
            embed.add_field(name="🟦 Blue Team Win Chance", value=f"**{blue_win_prob * 100:.2f}%**", inline=True)
            embed.add_field(name="🟥 Red Team Win Chance", value=f"**{red_win_prob * 100:.2f}%**", inline=True)

            # Let's show the drafted champs just to make sure.
            embed.add_field(name="Blue Draft", value=", ".join(blue_display), inline=False)
            embed.add_field(name="Red Draft", value=", ".join(red_display), inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"⚠️ An unexpected error occurred: {str(e)}")

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

            # Analyze every enemy and their bs
            for p in match_data['participants']:
                if p['teamId'] == enemy_team_id:
                    e_puuid = p.get('puuid')
                    riot_id = p.get('riotIdGlobalName', 'Unknown Player')
                    c_id = p['championId']
                    c_name = self.champ_dict.get(str(c_id), 'Unknown')

                    if p.get('bot', False) or not e_puuid:
                        embed.add_field(name=f"🤖 {c_name} (Bot)", value="No data available.", inline=False)
                        continue

                    # This call out get_champion_mastery function from RiotAPIClient Class in riot_api.py.
                    mastery = await self.riot.get_champion_mastery(e_puuid, c_id)

                    # This call out summoner ID function from RiotAPIClient Class in riot_api.py.
                    sum_id = p.get('summonerId') or await self.riot.get_summoner_id(e_puuid)

                    # This call out get_summoner_rank function from RiotAPIClient Class in riot_api.py.
                    rank = await self.riot.get_summoner_rank(sum_id) if sum_id else "Unranked"

                    embed.add_field(name=f"⚔️ {c_name} - {riot_id}", value=f"**Rank:** {rank}\n**Mastery:** {mastery:,} pts", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"⚠️ An unexpected error occurred: {str(e)}")

# Setup Hook or something whatever this is called.
async def setup(bot):
    await bot.add_cog(DraftCommands(bot, bot.riot_client, bot.ai_system, bot.meta_db, bot.champ_dict))