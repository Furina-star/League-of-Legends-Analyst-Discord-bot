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
        self._db = None  # Persistent connection

    async def init_db(self):
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA synchronous=NORMAL")

        await self._db.execute("""
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
        await self._db.execute("CREATE TABLE IF NOT EXISTS opt_outs (discord_id TEXT PRIMARY KEY)")
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS linked_accounts (
                discord_id TEXT PRIMARY KEY,
                puuid TEXT UNIQUE,
                riot_id TEXT,
                server TEXT
            )
        """)
        await self._db.execute("""
                CREATE TABLE IF NOT EXISTS ml_queue (
                    match_id TEXT PRIMARY KEY,
                    server TEXT
                )
            """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS ml_training_data (
                match_id TEXT PRIMARY KEY,
                blue_win INTEGER,
                payload TEXT 
            )
        """)
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_game_logs_discord ON game_logs(discord_id)")
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            logger.info("Database connection closed safely.")

    async def log_match(self, discord_id, match_id, kp, deaths, gpm, dpm, win):
        if await self.is_opted_out(discord_id): return

        try:
            await self._db.execute("""
                INSERT OR IGNORE INTO game_logs (discord_id, match_id, kp_percent, deaths, gold_per_min, dpm, win)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (str(discord_id), match_id, kp, deaths, gpm, dpm, int(win)))
            await self._db.commit()
        except Exception as e:
            logging.getLogger("discord").error(f"Failed to log match {match_id}: {e}")

    async def is_opted_out(self, discord_id):
        async with self._db.execute("SELECT 1 FROM opt_outs WHERE discord_id = ?", (str(discord_id),)) as cursor:
            return await cursor.fetchone() is not None

    # Link the account like connect the player to the database.
    async def link_account(self, discord_id: int, puuid: str, riot_id: str, server: str):
        await self._db.execute("""
            INSERT OR REPLACE INTO linked_accounts (discord_id, puuid, riot_id, server)
            VALUES (?, ?, ?, ?)
        """, (str(discord_id), puuid, riot_id, server))
        await self._db.commit()

    # Unlink the account
    async def unlink_account(self, discord_id):
        await self._db.execute("DELETE FROM linked_accounts WHERE discord_id = ?", (str(discord_id),))
        await self._db.commit()

    # Clean the logs if they unlink
    async def clear_user_logs(self, discord_id):
        await self._db.execute("DELETE FROM game_logs WHERE discord_id = ?", (str(discord_id),))
        await self._db.commit()

    # Get the Discord ID linked to a given PUUID (for anti-fraud checks)
    async def get_discord_id_by_puuid(self, puuid):
        async with self._db.execute("SELECT discord_id FROM linked_accounts WHERE puuid = ?", (puuid,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None

    # Get linked account
    async def get_linked_account(self, discord_id):
        async with self._db.execute("SELECT riot_id, puuid, server FROM linked_accounts WHERE discord_id = ?",
                                (str(discord_id),)) as cursor:
            return await cursor.fetchone()

    # Get all linked accounts
    async def get_all_linked_accounts(self) -> Iterable[Row]:
        async with self._db.execute("SELECT discord_id, puuid, riot_id, server FROM linked_accounts") as cursor:
            return await cursor.fetchall()

    # Queue a match for ML processing
    async def insert_ml_queue(self, match_id: str, server: str):
        await self._db.execute("INSERT OR IGNORE INTO ml_queue (match_id, server) VALUES (?, ?)", (match_id, server))
        await self._db.commit()

    # Fetch one match from the ML queue (returns None if empty)
    async def get_one_queued_match(self):
        async with self._db.execute("SELECT match_id, server FROM ml_queue LIMIT 1") as cursor:
            return await cursor.fetchone()

    # Remove a match from the ML queue after processing
    async def remove_from_queue(self, match_id: str):
        await self._db.execute("DELETE FROM ml_queue WHERE match_id = ?", (match_id,))
        await self._db.commit()

    # Save queue to the ml_training_data table after processing
    async def save_ml_data(self, match_id: str, blue_win: int, payload: str):
        await self._db.execute("INSERT OR REPLACE INTO ml_training_data (match_id, blue_win, payload) VALUES (?, ?, ?)",
                            (match_id, blue_win, payload))
        await self._db.commit()

    # Fetches the worst stats from the players
    async def get_hall_of_shame(self, server_member_ids):
        if not server_member_ids:
            return None

        placeholders = ','.join('?' for _ in server_member_ids)

        # Fetch everyone's aggregated stats in a single hit
        async with self._db.execute(f"""
            SELECT
                discord_id,
                AVG(kp_percent) as avg_kp,
                MAX(deaths) as max_deaths,
                AVG(gold_per_min) as avg_gpm,
                AVG(dpm) as avg_dpm,
                AVG(win) * 100 as avg_winrate,
                COUNT(match_id) as game_count
            FROM game_logs
            WHERE discord_id IN ({placeholders})
            GROUP BY discord_id
        """, server_member_ids) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return None

        # Let Python figure out the winners/losers instantly
        backpack = min(rows, key=lambda x: x["avg_kp"])
        jester = max(rows, key=lambda x: x["max_deaths"])
        pacifist = min(rows, key=lambda x: x["avg_dpm"])
        inter = min(rows, key=lambda x: x["avg_winrate"])
        addict = max(rows, key=lambda x: x["game_count"])
        starving = min(rows, key=lambda x: x["avg_gpm"])

        return {
            "backpack": (backpack["discord_id"], backpack["avg_kp"]),
            "jester": (jester["discord_id"], jester["max_deaths"]),
            "pacifist": (pacifist["discord_id"], pacifist["avg_dpm"]),
            "inter": (inter["discord_id"], inter["avg_winrate"]),
            "addict": (addict["discord_id"], addict["game_count"]),
            "starving": (starving["discord_id"], starving["avg_gpm"])
        }