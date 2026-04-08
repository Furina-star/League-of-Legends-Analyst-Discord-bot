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
import os, sys
import json
import requests
import re
from dotenv import load_dotenv
from riot_api import RiotAPIClient
from ai_wrapper import LeagueAI
import logging
import config

# A standard synchronous function to load JSON
def load_json_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# This creates and print debugs logs properly.
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/furina.log"),  # saves to a file
        logging.StreamHandler()              # still shows in console
    ]
)
logger = logging.getLogger(__name__)

# Initiate Data Dragon dictionary API  as a function
CACHE_FILE = "data/champion_cache.json"
def get_champion_mapping():
    try:
        # Fetch just the version number
        latest_version = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10).json()[0]

        # Check if cache exists and is up to date
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as f:
                cached_data = json.load(f)

                # If cache matches the live patch, use the cache
                if cached_data.get("version") == latest_version:
                    return cached_data.get("mapping")

        # If no cache exists, or the patch updated, download the heavy file
        champ_data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/en_US/champion.json", timeout=10).json()

        id_to_name = {str(info['key']): name for name, info in champ_data['data'].items()}
        id_to_name["-1"] = "None"

        # Save the new mapping and version to the cache file
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True) # Ensure 'data' folder exists
        with open(CACHE_FILE, "w") as f:
            json.dump({"version": latest_version, "mapping": id_to_name}, f, indent=4)
        return id_to_name

    except Exception as e:
        logger.error(f"Data Dragon error: {e}")

        # Just in case the Riot Server is down (Imagine RITO????)
        if os.path.exists(CACHE_FILE):
            logger.warning("Network Failed: Falling back to old local cache.")
            with open(CACHE_FILE, "r") as f:
                return json.load(f).get("mapping", {})

        return {} # Return an empty dictionary if everything fails

# Initiate Roles from Champion_Roles.json as a function
def load_meta_roles():
    try:
        with open('data/Champion_Roles.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logger.warning("⚠️ CRITICAL: Could not find data/Champion_Roles.json!")
        return {}

# Custom Prefix
def custom_prefix(bot, message):
    match = re.match(r'^(furina\s*|f\s*)', message.content, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return "!"  # Default fallback

# Initiate the bot
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
RIOT_KEY = os.getenv('RIOT_API_KEY')

if not TOKEN or not RIOT_KEY: # Stop the system if .env is not set up.
    sys.exit("Error: DISCORD_TOKEN and RIOT_API_KEY must be set in the .env file.")

intents = discord.Intents.default()
intents.message_content = True

# Creating a subclass of commands.Bot
class DiscordBot(commands.Bot):
    # This is a special function that runs once when the bot starts up, before it connects to Discord.
    async def setup_hook(self):
        logger.info("Running one-time setup...")

        # 🚀 Use asyncio to push the blocking file read to a background thread!
        self.meta_db = await asyncio.to_thread(load_json_file, config.META_PATH)
        self.champ_dict = await asyncio.to_thread(load_json_file, config.CHAMP_DICT_PATH)

        # Initialize APIs and AI here so they only load once!
        self.riot_client = RiotAPIClient(config.RIOT_KEY)
        self.ai_system = LeagueAI()

        # Attach the dictionaries and configs
        self.server_dict = config.SERVER_TO_REGION

        # Remove the default help
        self.remove_command('help')

        # Load Cogs
        await self.load_extension("cogs.draft_commands")
        await self.load_extension("cogs.general_commands")

        logger.info("All Cogs and Systems loaded successfully!")

    # This shutdown the API Session completely if the bot itself shut down
    async def close(self):
        if hasattr(self, 'riot_client'):
            await self.riot_client.close()
            logger.info("Riot API connection closed safely.")

        # Resume the normal Discord shutdown process
        await super().close()

    # This handle spamming and other common command errors gracefully, without crashing the bot or spamming the channel with error messages.
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"**Slow down!** You can use this command again in `{error.retry_after:.1f}` seconds.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You are missing some arguments! Check `f help` for the correct format.")
        elif isinstance(error, commands.CommandNotFound):
            # Ignore commands that don't exist, like if someone types 'f something, something'
            pass
        else:
            # If it's a real bug
            logger.error(f"Ignoring exception in command {ctx.command}:", exc_info=error)

bot = DiscordBot(command_prefix=custom_prefix, case_insensitive=True, intents=intents)

if __name__ == "__main__":
    logger.info("Downloading Data Dragon files...")
    champ_dict_cache = get_champion_mapping()
    meta_db_cache = load_meta_roles()


    @bot.event
    async def on_ready():
        # Set the bot's activity status to show the custom prefix and a fun message
        print(f'Logged in as {bot.user.name}')
        logger.info("Furina Architecture Online and Ready!")

    bot.run(TOKEN)
