"""

"""

import sqlite3

class DatabaseManager:
    def __init__(self, db_path="data/server_state.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
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
            # Table for opt-outs
            conn.execute("CREATE TABLE IF NOT EXISTS opt_outs (discord_id TEXT PRIMARY KEY)")

            # Table to link Discord IDs to Riot PUUIDs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS linked_accounts (
                    discord_id TEXT PRIMARY KEY,
                    puuid TEXT UNIQUE,
                    riot_id TEXT
                )
            """)

    def log_match(self, discord_id, match_id, kp, deaths, gpm, dpm, win):
        # Check if the user is opted out
        if self.is_opted_out(discord_id): return

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO game_logs (discord_id, match_id, kp_percent, deaths, gold_per_min, dpm, win)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(discord_id), match_id, kp, deaths, gpm, dpm, 1 if win else 0))
        except sqlite3.IntegrityError:
            pass # Match already tagged

    def is_opted_out(self, discord_id):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT 1 FROM opt_outs WHERE discord_id = ?", (str(discord_id),)).fetchone() is not None

    # Link the account
    def link_account(self, discord_id, puuid, riot_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO linked_accounts (discord_id, puuid, riot_id)
                VALUES (?, ?, ?)
            """, (str(discord_id), puuid, riot_id))

    # Unlink the account
    def unlink_account(self, discord_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM linked_accounts WHERE discord_id = ?", (str(discord_id),))

    # Check who owns a PUUID
    def get_discord_id_by_puuid(self, puuid):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT discord_id FROM linked_accounts WHERE puuid = ?", (puuid,))
            result = cursor.fetchone()
            return result[0] if result else None

    # Returns the (riot_id, puuid) of a user, or None if they are not linked
    def get_linked_account(self, discord_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT riot_id, puuid FROM linked_accounts WHERE discord_id = ?", (str(discord_id),))
            return cursor.fetchone()

    """
    # Future Implementation just in case, also uncomment the call in state_resolvers.py if you do
    # Wipes a user's past game logs from the Hall of Shame
    def clear_user_logs(self, discord_id):
        with sqlite3.connect(self.db_path) as conn:
            # Safely deletes all their previous matches from the records
            conn.execute("DELETE FROM game_logs WHERE discord_id = ?", (str(discord_id),))
    """

    # Fetches the worst stats from the past 7 days
    def get_hall_of_shame(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Lowest AVG KP%, min 3 games
            cursor.execute("""
                SELECT discord_id, AVG(kp_percent) as val 
                FROM game_logs 
                WHERE timestamp > DATETIME('now', '-7 days')
                  AND discord_id IS NOT NULL 
                  AND discord_id != 'None'
                GROUP BY discord_id 
                HAVING COUNT(match_id) >= 3 
                ORDER BY val ASC LIMIT 1
            """)
            backpack = cursor.fetchone()

            # Most Deaths in a single game
            cursor.execute("""
                SELECT discord_id, deaths as val 
                FROM game_logs 
                WHERE timestamp > DATETIME('now', '-7 days')
                  AND discord_id IS NOT NULL 
                  AND discord_id != 'None'
                ORDER BY val DESC LIMIT 1
            """)
            jester = cursor.fetchone()

            # Highest AVG GPM, min 3 games
            cursor.execute("""
                SELECT discord_id, AVG(gold_per_min) as val 
                FROM game_logs 
                WHERE timestamp > DATETIME('now', '-7 days')
                  AND discord_id IS NOT NULL 
                  AND discord_id != 'None'
                GROUP BY discord_id 
                HAVING COUNT(match_id) >= 3 
                ORDER BY val DESC LIMIT 1
            """)
            tax = cursor.fetchone()

            return {"backpack": backpack, "jester": jester, "tax": tax}