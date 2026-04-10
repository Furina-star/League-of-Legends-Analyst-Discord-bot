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
from utils.parsers import parse_winrate, find_duos, detect_autofill, sort_team_roles

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
    async def get_live_match(self, puuid: str, platform_override: Optional[str] = None) -> dict[str, Any] | list[Any] | None:
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
    async def get_match_history(self, puuid, count=20, queue_id=None, region_override=None):
        r = region_override or self.region
        url = f"https://{r}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}"
        if queue_id is not None:
            url += f"&queue={queue_id}"
        return await self._fetch(url, cache_ttl=300)

    # Initiate Match Details API as a function
    async def get_match_details(self, match_id, region_override=None):
        r = region_override or self.region
        url = f"https://{r}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return await self._fetch(url, cache_ttl=86400)

    # Initiate Top Masteries API as a function
    async def get_top_masteries(self, puuid: str, count: int = 3, platform_override: Optional[str] = None) -> list:
        if not puuid or puuid == "None":
            return []
        p = (platform_override or self.platform).lower()
        url = f"https://{p}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count={count}"
        data = await self._fetch(url, cache_ttl=3600)
        return data if isinstance(data, list) else []

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
        if not puuid or puuid == "None":
            return "Unranked"
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

    # Fetches mastery and rank concurrently for a team.
    async def _fetch_team_stats(self, players, server):
        async def fetch_rank_safe(puuid):
            return await self.get_summoner_rank(puuid, platform_override=server)

        wr_tasks = [fetch_rank_safe(puuid) for puuid, _, _ in players]
        mastery_tasks = [self.get_champion_mastery(puuid, c_id, platform_override=server) for puuid, _, c_id in players]

        wr_results = await asyncio.gather(*wr_tasks)

        # Pause for exactly 1 second to let Riot's 20-per-second limit reset
        await asyncio.sleep(1.0)

        masteries = await asyncio.gather(*mastery_tasks)

        winrates = [parse_winrate(res) for res in wr_results]
        avg_wr = sum(winrates) / len(winrates) if winrates else 50.0

        return winrates, masteries, avg_wr

    # Helper number one for fetching enemy data
    async def _fetch_single_enemy(self, c_name, riot_id, e_puuid, c_id, server, region, perks, inferred_position, keystone_db):
        # Check if Keystone was used
        if perks and 'perkIds' in perks and len(perks['perkIds']) > 0:
            keystone_id = str(perks['perkIds'][0])
            keystone_name = keystone_db.get(keystone_id, "Unknown Rune")
        else:
            keystone_name = "None"

        # Fetch their last 5 ranked matches (costs 1 API call per player)
        mastery_task = self.get_champion_mastery(e_puuid, c_id, platform_override=server)
        history_task = self.get_match_history(e_puuid, count=5, queue_id=420, region_override=region)

        # Fetch their top mastery champion
        top_mastery_task = self.get_top_masteries(e_puuid, count=3, platform_override=server)

        async def get_rank():
            await asyncio.sleep(1.5)
            return await self.get_summoner_rank(e_puuid, platform_override=server)

        mastery, rank, history, top_masteries = await asyncio.gather(
            mastery_task, get_rank(), history_task, top_mastery_task
        )

        # Safety fallback if history fails to load
        if not isinstance(history, list):
            history = []

        # Reuse already-fetched history IDs, get_match_details is cached 24h so repeat calls are free
        primary_role = await self.get_primary_role_from_history(history, e_puuid, region)
        is_autofilled = detect_autofill(primary_role, inferred_position)

        is_otp = False
        if top_masteries:
            top_champ_id = top_masteries[0].get('championId')
            top_points = top_masteries[0].get('championPoints', 0)

            if len(top_masteries) == 1:
                is_otp = top_champ_id == c_id
            else:
                second_points = top_masteries[1].get('championPoints', 1)
                is_otp = top_champ_id == c_id and top_points >= (second_points * 3)

        return c_name, riot_id, rank, mastery, history, keystone_name, is_otp, is_autofilled

    # Initiate fetching enemy data as a function, this is where we get the mastery, rank, and match history for each enemy player, and also check if any of them are duos.
    async def _fetch_enemy_data(self, match_data, enemy_team_id, server, region, champ_dict, keystone_db, role_db):
        bot_entries = []
        player_tasks = []

        # Sort enemy team to get inferred positions
        enemy_participants = [p for p in match_data['participants'] if p['teamId'] == enemy_team_id]

        # Build a position lookup: championId -> inferred position string
        sorted_champ_names = sort_team_roles(enemy_participants, champ_dict, role_db)
        INDEX_TO_POSITION = {0: "TOP", 1: "JUNGLE", 2: "MIDDLE", 3: "BOTTOM", 4: "UTILITY"}
        champ_to_position = {
            name: INDEX_TO_POSITION[i] for i, name in enumerate(sorted_champ_names)
        }

        for p in enemy_participants:
            c_name = champ_dict.get(str(p['championId']), 'Unknown')
            e_puuid = p.get('puuid')

            if p.get('bot', False) or not e_puuid:
                bot_entries.append(c_name)
            else:
                riot_id = p.get('riotId') or p.get('summonerName') or 'Unknown Player'
                inferred_position = champ_to_position.get(c_name, '')  # ← inferred from sort
                player_tasks.append(
                    self._fetch_single_enemy(
                        c_name, riot_id, e_puuid, p['championId'],
                        server, region, p.get('perks', {}), inferred_position,
                        keystone_db
                    )
                )

        # Wait for all players to finish fetching
        raw_results = await asyncio.gather(*player_tasks)

        # Extract just the IDs and Histories to pass to our Duo Detective
        histories = [(res[1], res[4]) for res in raw_results]
        duo_set = find_duos(histories)

        # Build the final list to send to the embed formatter
        final_players = []
        for c_name, riot_id, rank, mastery, _, keystone_name, is_otp, is_autofilled in raw_results:
            is_duo = riot_id in duo_set
            final_players.append((c_name, riot_id, rank, mastery, is_duo, keystone_name, is_otp, is_autofilled))

        return bot_entries, final_players

    # Initiate the primary role detection as a function.
    async def get_primary_role_from_history(self, match_ids: list, puuid: str, region: str) -> str:
        if not match_ids:
            return ""

        # Fetch all match details concurrently — 24h cache means repeat calls are FREE
        detail_tasks = [self.get_match_details(mid, region_override=region) for mid in match_ids]
        details = await asyncio.gather(*detail_tasks)

        role_counts = {}
        for match in details:
            if not isinstance(match, dict):
                continue
            for p in match.get('info', {}).get('participants', []):
                if p.get('puuid') == puuid:
                    role = p.get('teamPosition', '')
                    if role:
                        role_counts[role] = role_counts.get(role, 0) + 1
                    break

        return max(role_counts, key=role_counts.get) if role_counts else ""