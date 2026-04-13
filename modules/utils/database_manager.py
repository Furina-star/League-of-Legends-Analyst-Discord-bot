"""
The Database Manager is responsible for all interactions with the database.
It provides methods to log match data, manage linked accounts, and fetch statistics for the Hall of Shame.
By centralizing database operations in this class, we can ensure consistent data handling and make it easier to maintain and update our database schema in the future.
"""

import aiosqlite
import logging
from utils.logger_algorithm import initialize_logger

# Get the logging system
logger = initialize_logger()

class DatabaseManager:
    def __init__(self, db_path="data/server_state.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS game_logs (
                    discord_id TEXT,
                    match_id TEXT PRIMARY KEY,
                    kp_percent REAL,
                    deaths INTEGER,
                    gold_per_min REAL,
                    dpm REAL,
                    win INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("CREATE TABLE IF NOT EXISTS opt_outs (discord_id TEXT PRIMARY KEY)")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS linked_accounts (
                    discord_id TEXT PRIMARY KEY,
                    puuid TEXT UNIQUE,
                    riot_id TEXT
                )
            """)
            await conn.commit()

    async def log_match(self, discord_id, match_id, kp, deaths, gpm, dpm, win):
        if await self.is_opted_out(discord_id): return

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT OR IGNORE INTO game_logs (discord_id, match_id, kp_percent, deaths, gold_per_min, dpm, win)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(discord_id), match_id, kp, deaths, gpm, dpm, int(win)))
                await conn.commit()
        except Exception as e:
            logging.getLogger("discord").error(f"Failed to log match {match_id}: {e}")

    async def is_opted_out(self, discord_id):
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT 1 FROM opt_outs WHERE discord_id = ?", (str(discord_id),)) as cursor:
                return await cursor.fetchone() is not None

    # Link the account
    async def link_account(self, discord_id, puuid, riot_id):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO linked_accounts (discord_id, puuid, riot_id)
                VALUES (?, ?, ?)
            """, (str(discord_id), puuid, riot_id))
            await conn.commit()

    # Unlink the account
    async def unlink_account(self, discord_id):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM linked_accounts WHERE discord_id = ?", (str(discord_id),))
            await conn.commit()

    # Clean the logs if they unlink
    async def clear_user_logs(self, discord_id):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM game_logs WHERE discord_id = ?", (str(discord_id),))
            await conn.commit()

    # Get the Discord ID linked to a given PUUID (for anti-fraud checks)
    async def get_discord_id_by_puuid(self, puuid):
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT discord_id FROM linked_accounts WHERE puuid = ?", (puuid,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None

    # Get linked account
    async def get_linked_account(self, discord_id):
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT riot_id, puuid FROM linked_accounts WHERE discord_id = ?",
                                    (str(discord_id),)) as cursor:
                return await cursor.fetchone()

    # Fetches the worst stats from the past 7 days
    async def get_hall_of_shame(self):
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("""
                SELECT discord_id, AVG(kp_percent) as val FROM game_logs 
                WHERE timestamp > DATETIME('now', '-7 days') AND discord_id IS NOT NULL AND discord_id != 'None'
                GROUP BY discord_id HAVING COUNT(match_id) >= 3 ORDER BY val ASC LIMIT 1
            """) as cursor:
                backpack = await cursor.fetchone()

            async with conn.execute("""
                SELECT discord_id, deaths as val FROM game_logs 
                WHERE timestamp > DATETIME('now', '-7 days') AND discord_id IS NOT NULL AND discord_id != 'None'
                ORDER BY val DESC LIMIT 1
            """) as cursor:
                jester = await cursor.fetchone()

            async with conn.execute("""
                SELECT discord_id, AVG(gold_per_min) as val FROM game_logs 
                WHERE timestamp > DATETIME('now', '-7 days') AND discord_id IS NOT NULL AND discord_id != 'None'
                GROUP BY discord_id HAVING COUNT(match_id) >= 3 ORDER BY val DESC LIMIT 1
            """) as cursor:
                tax = await cursor.fetchone()

            return {"backpack": backpack, "jester": jester, "tax": tax}