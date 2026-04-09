"""
This is the part of the code that directly interacts with Riot's servers to fetch data about players, matches, and more.
It handles all the API calls, rate limits, and data parsing to provide clean and usable information for the rest of the bot to work with.
"""

import aiohttp
import asyncio
import random
import logging
from typing import Optional, Union, Dict, Any, List
from urllib.parse import quote
from utils.cache import RiotCache

logger = logging.getLogger(__name__)


class RiotAPIClient:
    # This sill goofy ass remembers the key and regions
    def __init__(self, api_key: str, default_platform: str = "sg2", default_region: str = "asia") -> None:
        self.api_key = api_key
        self.platform = default_platform
        self.region = default_region
        self._session = None
        self.cache = RiotCache()
        self._semaphore = asyncio.Semaphore(15)

    # Set up the database when the bot starts
    async def setup_cache(self):
        await self.cache.setup()

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

        if hasattr(self, 'cache') and self.cache is not None:
            await self.cache.close()

    # This function handles the API calls at its maximum efficiency while respecting rate limits and caching results to minimize unnecessary calls.
    async def _fetch(self, url: str, max_retries: int = 3, cache_ttl: int = 0) -> Optional[
        Union[Dict[str, Any], List[Any]]]:
        # Check the cache first before making an API call! If cache_ttl is set to 0, we skip caching and always fetch fresh data.
        if cache_ttl > 0:
            cached_data = await self.cache.get(url)
            if cached_data: return cached_data

        # The bouncer
        async with self._semaphore:
            headers = {"X-Riot-Token": self.api_key}
            session = self._get_session()

            for attempt in range(max_retries):
                try:
                    async with session.get(url, headers=headers, timeout=10) as response:
                        # 200 means its good other than that it's an error like 429 below which gives Rate Limit Exceeded
                        if response.status == 200:
                            data = await response.json()
                            # 2. Save successful fetches to the cache for next time!
                            if cache_ttl > 0:
                                await self.cache.set(url, data, ttl_seconds=cache_ttl)
                            return data
                        # 429 means the API rate limit was exceeded, so we need to wait before retrying
                        elif response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 5))
                            logger.warning(f"[RATE LIMIT] Waiting {retry_after}s... (Attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(retry_after)
                        # Exponential backoff + Jitter for server errors
                        elif response.status >= 500:
                            sleep_time = (2 ** attempt) + random.uniform(0.1, 1.0)
                            logger.warning(f"[SERVER ERROR {response.status}] Retrying in {sleep_time:.2f}s...")
                            await asyncio.sleep(sleep_time)
                        # This error is the API itself
                        else:
                            logger.error(f"[API ERROR {response.status}] Failed to fetch: {url}")
                            return None

                # Catch actual internet drops and timeouts!
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    sleep_time = (2 ** attempt) + random.uniform(0.1, 1.0)
                    logger.warning(f"[NETWORK ERROR] {e}. Retrying in {sleep_time:.2f}s...")
                    await asyncio.sleep(sleep_time)

        logger.warning(f"[MAX RETRIES] Gave up on fetching: {url}")
        return None

    # Initiate getting the PUUID of the player as a function
    async def get_puuid(self, game_name: str, tag_line: str, region_override: Optional[str] = None) -> Optional[str]:
        r = region_override or self.region
        encoded_name = quote(game_name)
        url = f"https://{r}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{tag_line}"
        data = await self._fetch(url, cache_ttl=86400)
        if isinstance(data, dict):
            return data.get('puuid')
        return None

    # Initiate Live Match API as a function
    async def get_live_match(self, puuid: str, platform_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
        p = platform_override or self.platform
        url = f"https://{p}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        return await self._fetch(url, cache_ttl=0)

    # Initiate Champion Mastery API as a function
    async def get_champion_mastery(self, puuid: str, champ_id: int, platform_override: Optional[str] = None) -> int:
        if not puuid:
            return 0

        p = (platform_override or self.platform).lower()
        url = f"https://{p}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champ_id}"
        data = await self._fetch(url, cache_ttl=3600)
        if isinstance(data, dict):
            return data.get('championPoints', 0)
        return 0

    # Initiate Match History API as a function
    async def get_match_history(self, puuid, count=20, queue_id=420, region_override=None):
        r = region_override or self.region
        url = f"https://{r}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue_id}&start=0&count={count}"
        return await self._fetch(url, cache_ttl=300)

    # Initiate Match Details API as a function
    async def get_match_details(self, match_id, region_override=None):
        r = region_override or self.region
        url = f"https://{r}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return await self._fetch(url, cache_ttl=86400)

    # Helper function to format the rank string
    @staticmethod
    def _format_rank_str(queue_data):
        tier = queue_data.get('tier', 'UNRANKED').title()
        rank = queue_data.get('rank', '')
        lp = queue_data.get('leaguePoints', 0)
        wins = queue_data.get('wins', 0)
        losses = queue_data.get('losses', 0)
        hot_streak = queue_data.get('hotStreak', False)
        total_games = wins + losses

        # Adding a fire emoji for players on a win streak
        streak_icon = " 🔥 (Hot Streak)" if hot_streak else ""

        base_str = f"{tier} {rank} ({lp} LP){streak_icon}"
        if total_games > 0:
            winrate = (wins / total_games) * 100
            return f"{base_str} | **{winrate:.1f}% WR** ({total_games} games)"
        return base_str

    # Initiate Rank API as a function
    async def get_summoner_rank(self, puuid: str, platform_override: Optional[str] = None) -> str:
        p = (platform_override or self.platform).lower()
        url = f"https://{p}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"

        data = await self._fetch(url, cache_ttl=3600)

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