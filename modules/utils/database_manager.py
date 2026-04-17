"""
The Database Manager is responsible for all interactions with the database.
It provides methods to log match data, manage linked accounts, and fetch statistics for the Hall of Shame.
By centralizing database operations in this class, we can ensure consistent data handling and make it easier to maintain and update our database schema in the future.
"""
from sqlite3 import Row
from typing import Iterable

import aiosqlite
import logging
    
# Get the logging system
logger = logging.getLogger(__name__)

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
                    riot_id TEXT,
                    server TEXT
                )
            """)
            await conn.execute("""
                    CREATE TABLE IF NOT EXISTS ml_queue (
                        match_id TEXT PRIMARY KEY,
                        server TEXT
                    )
                """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ml_training_data (
                    match_id TEXT PRIMARY KEY,
                    blue_win INTEGER,
                    payload TEXT 
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

    # Link the account like connect the player to the database.
    async def link_account(self, discord_id: int, puuid: str, riot_id: str, server: str):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO linked_accounts (discord_id, puuid, riot_id, server)
                VALUES (?, ?, ?, ?)
            """, (str(discord_id), puuid, riot_id, server))
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

    # Get all linked accounts
    async def get_all_linked_accounts(self) -> Iterable[Row]:
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT discord_id, puuid, riot_id, server FROM linked_accounts") as cursor:
                return await cursor.fetchall()

    async def insert_ml_queue(self, match_id: str, server: str):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("INSERT OR IGNORE INTO ml_queue (match_id, server) VALUES (?, ?)", (match_id, server))
            await conn.commit()

    async def get_one_queued_match(self):
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute("SELECT match_id, server FROM ml_queue LIMIT 1") as cursor:
                return await cursor.fetchone()

    async def remove_from_queue(self, match_id: str):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM ml_queue WHERE match_id = ?", (match_id,))
            await conn.commit()

    async def save_ml_data(self, match_id: str, blue_win: int, payload: str):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("INSERT OR REPLACE INTO ml_training_data (match_id, blue_win, payload) VALUES (?, ?, ?)",
                               (match_id, blue_win, payload))
            await conn.commit()

    # Fetches the worst stats from the players
    async def get_hall_of_shame(self, server_member_ids: list):
        if not server_member_ids:
            return {}

        # Creates a dynamic string of question marks like "?, ?, ?" based on server size
        placeholders = ', '.join('?' for _ in server_member_ids)

        async with aiosqlite.connect(self.db_path) as conn:
            # Backpack
            async with conn.execute(f"""
                SELECT discord_id, AVG(kp_percent) as val FROM game_logs 
                WHERE discord_id IN ({placeholders})
                GROUP BY discord_id ORDER BY val ASC LIMIT 1
            """, server_member_ids) as cursor:
                backpack = await cursor.fetchone()

            #Jester
            async with conn.execute(f"""
                SELECT discord_id, deaths as val FROM game_logs 
                WHERE discord_id IN ({placeholders})
                ORDER BY val DESC LIMIT 1
            """, server_member_ids) as cursor:
                jester = await cursor.fetchone()

            # Tax Collector
            async with conn.execute(f"""
                SELECT discord_id, AVG(gold_per_min) as val FROM game_logs 
                WHERE discord_id IN ({placeholders})
                GROUP BY discord_id ORDER BY val DESC LIMIT 1
            """, server_member_ids) as cursor:
                tax = await cursor.fetchone()

            # Pacifist
            async with conn.execute(f"""
                SELECT discord_id, AVG(dpm) as val FROM game_logs 
                WHERE discord_id IN ({placeholders})
                GROUP BY discord_id ORDER BY val ASC LIMIT 1
            """, server_member_ids) as cursor:
                pacifist = await cursor.fetchone()

            # Inter
            async with conn.execute(f"""
                SELECT discord_id, AVG(win) * 100 as val FROM game_logs 
                WHERE discord_id IN ({placeholders})
                GROUP BY discord_id ORDER BY val ASC LIMIT 1
            """, server_member_ids) as cursor:
                inter = await cursor.fetchone()

            # Addict
            async with conn.execute(f"""
                SELECT discord_id, COUNT(match_id) as val FROM game_logs 
                WHERE discord_id IN ({placeholders})
                GROUP BY discord_id ORDER BY val DESC LIMIT 1
            """, server_member_ids) as cursor:
                addict = await cursor.fetchone()

            # Starving
            async with conn.execute(f"""
                SELECT discord_id, AVG(gold_per_min) as val FROM game_logs 
                WHERE discord_id IN ({placeholders})
                GROUP BY discord_id ORDER BY val ASC LIMIT 1
            """, server_member_ids) as cursor:
                starving = await cursor.fetchone()

            return {
                "backpack": backpack,
                "jester": jester,
                "tax": tax,
                "pacifist": pacifist,
                "inter": inter,
                "addict": addict,
                "starving": starving
            }