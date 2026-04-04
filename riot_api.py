import aiohttp
import asyncio
from urllib.parse import quote

class RiotAPIClient:
    # This sill goofy ass remembers the key and regions
    def __init__(self, api_key, default_platform="sg2", default_region="asia"):
        self.api_key = api_key
        self.platform = default_platform
        self.region = default_region

    # This method is a placeholder for fetching data from the Riot API.
    @staticmethod
    async def _fetch(url, max_retries=3):
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                async with session.get(url) as response:
                    # This basically means success 200 is the success code for Riot
                    if response.status == 200:
                        return await response.json()
                    # This handle the Rate limit which is 429
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 5))
                        print(f"⚠️ [RATE LIMIT] Riot API paused us. Waiting {retry_after} seconds... (Attempt {attempt + 1}/{max_retries})")

                        # Tell Python to wait without freezing the bot
                        await asyncio.sleep(retry_after)

                    else:
                        print(f"❌ [API ERROR {response.status}] Failed to fetch: {url}")
                        return None

            print(f"🛑 [MAX RETRIES] Gave up on fetching: {url}")
            return None

    # Initiate getting the PUUID of the player as a function
    async def get_puuid(self, game_name, tag_line):
        encoded_name = quote(game_name)
        url = f"https://{self.region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{tag_line}?api_key={self.api_key}"
        data = await self._fetch(url)
        if isinstance(data, dict):
            return data.get('puuid')
        return None

    # Initiate Live Match API as a function
    async def get_live_match(self, puuid):
        url = f"https://{self.platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}?api_key={self.api_key}"
        return await self._fetch(url)

    # Initiate Champion Mastery API as a function
    async def get_champion_mastery(self, puuid, champ_id):
        url = f"https://{self.platform}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champ_id}?api_key={self.api_key}"
        data = await self._fetch(url)
        if isinstance(data, dict):
            return data.get('championPoints', 0)
        return 0

    # Initiate Summoner ID API as a function
    async def get_summoner_id(self, puuid):
        url = f"https://{self.platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={self.api_key}"
        data = await self._fetch(url)
        if isinstance(data, dict):
            return data.get('id')
        return None

    # Initiate Match History API as a function
    async def get_match_history(self, puuid, count=20, queue_id=420):
        url = f"https://{self.region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue_id}&start=0&count={count}&api_key={self.api_key}"
        return await self._fetch(url)

    # Initiate Match Details API as a function
    async def get_match_details(self, match_id):
        url = f"https://{self.region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={self.api_key}"
        return await self._fetch(url)

    # Initiate Solo/Duo Rank API as a function
    async def get_summoner_rank(self, summoner_id):
        url = f"https://{self.platform}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={self.api_key}"
        data = await self._fetch(url)

        solo_rank = None
        flex_rank = None

        if isinstance(data, list):
            for queue in data:
                # The math for whichever queue they're in, we want to show the tier, rank, LP, and winrate if they have any games played
                tier = queue.get('tier', 'UNRANKED').title()  # .title() makes 'GOLD' look like 'Gold'
                rank = queue.get('rank', '')
                lp = queue.get('leaguePoints', 0)

                wins = queue.get('wins', 0)
                losses = queue.get('losses', 0)
                total_games = wins + losses

                # Format the winrate string
                if total_games > 0:
                    winrate = (wins / total_games) * 100
                    rank_str = f"{tier} {rank} ({lp} LP) | **{winrate:.1f}% WR** ({total_games} games)"
                else:
                    rank_str = f"{tier} {rank} ({lp} LP)"

                # Assign it to the correct variable
                if queue.get('queueType') == 'RANKED_SOLO_5x5':
                    solo_rank = f"**Solo:** {rank_str}"
                elif queue.get('queueType') == 'RANKED_FLEX_SR':
                    flex_rank = f"**Flex:** {rank_str}"

        # Decide what to return to Discord
        if solo_rank and flex_rank:
            return f"{solo_rank}\n{flex_rank}"
        elif solo_rank:
            return solo_rank
        elif flex_rank:
            return flex_rank

        return "Unranked" 