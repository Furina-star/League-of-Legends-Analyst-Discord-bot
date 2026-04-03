import aiohttp
from urllib.parse import quote

class RiotAPIClient:
    # This sill goofy ass remembers the key
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.riotgames.com"

    # This method is a placeholder for fetching data from the Riot API.
    async def _fetch(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None

    # Initiate getting the PUUID of the player
    async def get_puuid(self, game_name, tag_line):
        encoded_name = quote(game_name)
        url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{tag_line}?api_key={self.api_key}"
        data = await self._fetch(url)
        return data.get('puuid') if data else None

    # Initiate Live Match API as a function
    async def get_live_match(self, puuid):
        url = f"https://sg2.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}?api_key={self.api_key}"
        return await self._fetch(url)

    # Initiate Champion Mastery API as a function
    async def get_champion_mastery(self, puuid, champ_id):
        url = f"https://sg2.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champ_id}?api_key={self.api_key}"
        data = await self._fetch(url)
        return data.get('championPoints', 0) if data else 0

    # Initiate Summoner ID
    async def get_summoner_id(self, puuid):
        url = f"https://sg2.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={self.api_key}"
        data = await self._fetch(url)
        return data.get('id') if data else None

    # Initiate Solo/Duo Rank API as a function
    async def get_summoner_rank(self, summoner_id):
        url = f"https://sg2.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={self.api_key}"
        data = await self._fetch(url)

        if data:
            for queue in data:
                if queue.get('queueType') == 'RANKED_SOLO_5x5':
                    return f"{queue['tier']} {queue['rank']} ({queue['leaguePoints']} LP)"
        return "Unranked"  # Default to Unranked if they have no rank or API call fails