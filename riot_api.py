"""
This is the part of the code that directly interacts with Riot's servers to fetch data about players, matches, and more.
It handles all the API calls, rate limits, and data parsing to provide clean and usable information for the rest of the bot to work with.
"""

import aiohttp
import asyncio
from urllib.parse import quote
import logging
from typing import Optional, Dict, Any, List, Union

# Get the logging system
logger = logging.getLogger(__name__)

class RiotAPIClient:
    # This sill goofy ass remembers the key and regions
    def __init__(self, api_key: str, default_platform: str = "sg2", default_region: str = "asia") -> None:
        self.api_key = api_key
        self.platform = default_platform
        self.region = default_region
        self._session = None

    # Safely get or create session
    def _get_session(self):
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    # Close the session when the bot shuts down
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _fetch(self, url: str, max_retries: int = 3) -> Optional[Union[Dict[str, Any], List[Any]]]:
        headers = {"X-Riot-Token": self.api_key}
        session = self._get_session()

        for attempt in range(max_retries):
            async with session.get(url, headers=headers) as response:
                # 200 means its good other than that it's an error like 429 below which gives Rate Limit Exceeded
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"[RATE LIMIT] Waiting {retry_after}s... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_after)
                else:
                    logger.error(f"[API ERROR {response.status}] Failed to fetch: {url}")
                    return None

        logger.warning(f"[MAX RETRIES] Gave up on fetching: {url}")
        return None

    # Initiate getting the PUUID of the player as a function
    async def get_puuid(self, game_name: str, tag_line: str, region_override: Optional[str] = None) -> Optional[str]:
        r= region_override or self.region
        encoded_name = quote(game_name)
        url = f"https://{r}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{tag_line}"
        data = await self._fetch(url)
        if isinstance(data, dict):
            return data.get('puuid')
        return None

    # Initiate Live Match API as a function
    async def get_live_match(self, puuid: str, platform_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
        p = platform_override or self.platform
        url = f"https://{p}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        return await self._fetch(url)

    # Initiate Champion Mastery API as a function
    async def get_champion_mastery(self, puuid: str, champ_id: int, platform_override: Optional[str] = None) -> int:
        if not puuid:
            return 0

        p = platform_override or self.platform
        url = f"https://{p}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champ_id}"
        data = await self._fetch(url)
        if isinstance(data, dict):
            return data.get('championPoints', 0)
        return 0

    # Initiate Summoner ID API as a function
    async def get_summoner_id(self, puuid: str, platform_override: Optional[str] = None) -> Optional[str]:
        if not puuid:
            return None

        p = platform_override or self.platform
        url = f"https://{p}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        data = await self._fetch(url)
        if isinstance(data, dict):
            return data.get('id')
        return None

    # Initiate Match History API as a function
    async def get_match_history(self, puuid, count=20, queue_id=420, platform_override=None):
        p = platform_override or self.platform
        url = f"https://{p}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue_id}&start=0&count={count}"
        return await self._fetch(url)

    # Initiate Match Details API as a function
    async def get_match_details(self, match_id, platform_override=None):
        p = platform_override or self.platform
        url = f"https://{p}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return await self._fetch(url)

    # Helper function to format the rank string
    @staticmethod
    def _format_rank_str(queue_data):
        tier = queue_data.get('tier', 'UNRANKED').title()
        rank = queue_data.get('rank', '')
        lp = queue_data.get('leaguePoints', 0)
        wins = queue_data.get('wins', 0)
        losses = queue_data.get('losses', 0)
        total_games = wins + losses

        base_str = f"{tier} {rank} ({lp} LP)"
        if total_games > 0:
            winrate = (wins / total_games) * 100
            return f"{base_str} | **{winrate:.1f}% WR** ({total_games} games)"
        return base_str

    # Initiate Solo/Duo Rank API as a function
    async def get_summoner_rank(self, summoner_id: str, platform_override: Optional[str] = None) -> str:
        p = platform_override or self.platform
        url = f"https://{p}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        data = await self._fetch(url)

        if not isinstance(data, list) or not data:
            return "Unranked"

        ranks_dict = {}
        for queue in data:
            q_type = queue.get('queueType')
            if q_type == 'RANKED_SOLO_5x5':
                ranks_dict['Solo'] = f"**Solo:** {self._format_rank_str(queue)}"
            elif q_type == 'RANKED_FLEX_SR':
                ranks_dict['Flex'] = f"**Flex:** {self._format_rank_str(queue)}"

        results = []
        if 'Solo' in ranks_dict:
            results.append(ranks_dict['Solo'])
        if 'Flex' in ranks_dict:
            results.append(ranks_dict['Flex'])

        return "\n".join(results) if results else "Unranked"