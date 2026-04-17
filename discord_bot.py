"""
The main Discord bot file.
This is where the bot is initiated, the APIs are called, and the Cogs are loaded.
The main purpose of this file is to set up the architecture of the bot and handle any global events or errors that may occur.
The actual commands and logic for the draft system are handled in the Cogs.
This separate files that can be easily maintained and updated without affecting the core functionality of the bot.
This separation of concerns allows for a cleaner and more organized codebase, making it easier to debug and add new features in the future.
"""

import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import traceback
import config
from services.riot_api import RiotAPIClient
from services.ai_wrapper import LeagueAI
from modules.utils.translator import DiscordTranslator
from modules.utils.logger_algorithm import initialize_logger
from modules.utils.data_loader import load_champion_mapping, META_DB, ROLE_DB, RUNE_DB, SYNERGY_MATRIX
from modules.utils.database_manager import DatabaseManager

# Get the logging system
logger = initialize_logger()

# Creating a subclass of commands.Bot
class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = False
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        # Pre declare all instance variables
        self.db = None
        self.patch_version = None
        self.champ_dict = {}
        self.meta_db = {}
        self.role_db = {}
        self.keystone_db = {}
        self.synergy_matrix = {}
        self.server_dict = {}
        self.riot_client = None
        self.ai_system = None

    # This is a special function that runs once when the bot starts up, before it connects to Discord.
    async def setup_hook(self):
        logger.info("Running one-time setup...")

        # Initialize Database once and attach to bot
        self.db = DatabaseManager()
        await self.db.init_db()

        # Run the blocking Data Dragon update in a background thread
        self.patch_version, self.champ_dict = await asyncio.to_thread(load_champion_mapping)

        # Initialize Data
        self.meta_db = META_DB
        self.role_db = ROLE_DB
        self.keystone_db = RUNE_DB
        self.synergy_matrix = SYNERGY_MATRIX
        self.server_dict = config.PLATFORM_ROUTING

        # Initialize APIs
        self.riot_client = RiotAPIClient(config.RIOT_KEY)
        await self.riot_client.setup_cache()

        # Package your constants into a safe dictionary
        bot_config_dict = {
            'BASE_WINRATE': config.BASE_WINRATE,
            'FIRST_TIME_THRESHOLD': config.FIRST_TIME_THRESHOLD,
            'FIRST_TIME_PENALTY': config.FIRST_TIME_PENALTY,
            'OTP_THRESHOLD': config.OTP_THRESHOLD,
            'OTP_MAX_CAP': config.OTP_MAX_CAP,
            'OTP_BUFF_MULTIPLIER': config.OTP_BUFF_MULTIPLIER,
            'EMBEDDING_DIM': config.EMBEDDING_DIM,
            'DROPOUT_RATE': config.DROPOUT_RATE
        }

        # Initialize AI
        try:
            self.ai_system = LeagueAI(
                bot_config=bot_config_dict,
                synergy_matrix=self.synergy_matrix,
                meta_db=self.meta_db
            )
            logger.info("Deep Learning Model loaded perfectly.")
        except Exception as e:
            logger.error(f"Failed to load ML Model: {e}")

        # Load Cogs (Make sure to load your new general_commands cog where /help is!)
        try:
            initial_extensions = [
                "cogs.draft_commands",
                "cogs.general_commands",
                "cogs.stats_commands",
                "cogs.leaderboard_commands",
                "cogs.live_tracker"
            ]

            logger.info("Starting extension load...")

            for extension in initial_extensions:
                # Inner catch: Protects individual files
                try:
                    await self.load_extension(extension)
                    logger.info(f"Successfully loaded: {extension}")
                except Exception as e:
                    logger.error(f"Failed to load {extension}: {e}")

            logger.info("Finished loading all extensions!")

        except Exception as fatal_error:
            # This only triggers if something goes horribly wrong with the loop itself
            logger.critical(f"CRITICAL BOOT ERROR: {fatal_error}")

        # Sync Translator
        logger.info("Setting up Translator...")
        await self.tree.set_translator(DiscordTranslator())

        # Set the error handler for the translator to log errors without crashing the bot
        self.tree.on_error = self.on_tree_error

        # Sync slash commands
        logger.info("Syncing slash commands to Discord...")
        await self.tree.sync()
        logger.info("Slash commands and Translator synced successfully!")

    # Global Error handler
    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        # Handles cooldowns
        if isinstance(error, app_commands.CommandOnCooldown):
            cooldown_msg = f"**Slow down!** You can use this command again in `{error.retry_after:.1f}` seconds."
            if not interaction.response.is_done():
                await interaction.response.send_message(cooldown_msg, ephemeral=True)
            else:
                await interaction.followup.send(cooldown_msg, ephemeral=True)
            return 

        # Handle actual crashes and bugs
        original_error = getattr(error, 'original', error)

        # Print the detailed traceback to your server console
        logger.error(f"CRASH in command '/{interaction.command.name}':")
        traceback.print_exception(type(original_error), original_error, original_error.__traceback__)

        # Send a polite, hidden message to the user
        error_msg = "**A critical error occurred while processing your request.**\nWill fix it as soon as possible! If this keeps happening, please contact the bot owner."

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(error_msg, ephemeral=True)
            else:
                await interaction.followup.send(error_msg, ephemeral=True)
        except discord.HTTPException:
            # If Discord's servers are dying, just ignore it.
            pass

    # Safely close API Connection and the database
    async def close(self):
        if hasattr(self, 'riot_client') and self.riot_client:
            await self.riot_client.close()
            logger.info("Riot API connection closed safely.")

        if hasattr(self, 'db') and self.db:
            await self.db.close()

        await super().close()

if __name__ == "__main__":
    if not config.DISCORD_TOKEN or not config.RIOT_KEY:
        sys.exit("Error: DISCORD_TOKEN and RIOT_API_KEY must be set in the .env file.")

    required_data_files = {
        config.META_PATH: "scripts/build_meta.py",
        config.ROLES_PATH: "scripts/update_roles.py",
        config.SYNERGY_PATH: "scripts/build_synergy_matrix.py",
    }
    for filepath, script in required_data_files.items():
        if not os.path.exists(filepath):
            logger.warning(f"Missing: {filepath} — run `python {script}` to generate it.")

    bot = DiscordBot()

    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user.name}")

        # Give a status for the bot just a nice touch
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the Rift"))

        logger.info("Furina is Online and Ready!")

    bot.run(config.DISCORD_TOKEN)