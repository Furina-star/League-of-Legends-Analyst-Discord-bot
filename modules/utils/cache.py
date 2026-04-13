"""
This module provides a caching mechanism for Riot API responses using an SQLite database.
It allows you to store and retrieve cached data based on a unique key, which can be the API endpoint and parameters.
The cache entries have an expiration time, after which they will be considered stale and will be removed from the cache.
"""

import aiosqlite
import time
import json
import os

SCRIPT_DIR = str(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = str(os.path.dirname(SCRIPT_DIR))
ROOT_DIR = str(os.path.dirname(MODULES_DIR))

DEFAULT_DB_PATH = str(os.path.join(ROOT_DIR, "data", "riot_cache.db"))

class RiotCache:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        self._db = None

    # Creates the database if it doesn't exist and keeps the connection open
    async def setup(self):
        if self._db is None:
            # 2. Ensure the 'data' directory actually exists before SQLite tries to access it
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS riot_data (
                    endpoint TEXT PRIMARY KEY,
                    data TEXT,
                    expire_time REAL
                )
            """)
            await self._db.commit()

    # Retrieves cached data for a given key if it exists and is not expired
    async def get(self, endpoint: str):
        # Fallback just in case setup wasn't called
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT data, expire_time FROM riot_data WHERE endpoint = ?",
                                    (endpoint,)) as cursor:
            row = await cursor.fetchone()
            if row:
                data, expire_time = row
                if time.time() < expire_time:
                    return json.loads(data)  # Valid???? return the data
                else:
                    # Expired??? then delete it
                    await self._db.execute("DELETE FROM riot_data WHERE endpoint = ?", (endpoint,))
                    await self._db.commit()
        return None

    # Stores data in the cache with an expiration time
    async def set(self, endpoint: str, data, ttl_seconds: int = 7200):
        if self._db is None:
            await self.setup()

        expire_time = time.time() + ttl_seconds

        await self._db.execute("""
            INSERT OR REPLACE INTO riot_data (endpoint, data, expire_time)
            VALUES (?, ?, ?)
        """, (endpoint, json.dumps(data), expire_time))
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None